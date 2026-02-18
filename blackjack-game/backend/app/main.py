from __future__ import annotations

import sys
import os
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from logic_game import Game  # noqa: E402


def _card_asset_url(image_path: str) -> str:
    filename = Path(image_path).name
    return f"/assets/{filename}"


def _is_blackjack(player) -> bool:
    return len(player.hand) == 2 and player.score == 21


def _is_golden_blackjack(player) -> bool:
    return len(player.hand) == 2 and all(card.rank.value == "A" for card in player.hand)


@dataclass
class PlayerSeat:
    player_id: str
    name: str
    stood: bool = False
    resolved: bool = False
    result: str = ""


@dataclass
class Room:
    room_id: str
    host_id: str
    seats: List[PlayerSeat]
    max_players: int
    phase: str = "waiting"
    current_player_index: int = 0
    game: Optional[Game] = None

    def find_player_index(self, player_id: str) -> int:
        for idx, seat in enumerate(self.seats):
            if seat.player_id == player_id:
                return idx
        return -1


class CreateRoomRequest(BaseModel):
    player_name: str = Field(min_length=1, max_length=30)
    max_players: int = Field(ge=1, le=8)


class JoinRoomRequest(BaseModel):
    player_name: str = Field(min_length=1, max_length=30)


class StartGameRequest(BaseModel):
    player_id: str


class ActionRequest(BaseModel):
    player_id: str
    action: str


class RoomStateResponse(BaseModel):
    room_id: str
    phase: str
    current_player_index: int
    your_player_index: Optional[int]
    players: list
    dealer: dict
    can_start: bool
    can_act: bool
    results: list


class RoomManager:
    def __init__(self):
        self.rooms: Dict[str, Room] = {}
        self.lock = Lock()

    def _new_player_id(self) -> str:
        return uuid.uuid4().hex[:12]

    def _new_room_id(self) -> str:
        return uuid.uuid4().hex[:6].upper()

    def create_room(self, player_name: str, max_players: int) -> dict:
        with self.lock:
            room_id = self._new_room_id()
            player_id = self._new_player_id()
            room = Room(
                room_id=room_id,
                host_id=player_id,
                seats=[PlayerSeat(player_id=player_id, name=player_name.strip())],
                max_players=max_players,
            )
            self.rooms[room_id] = room
            return {"room_id": room_id, "player_id": player_id}

    def join_room(self, room_id: str, player_name: str) -> dict:
        with self.lock:
            room = self.rooms.get(room_id)
            if not room:
                raise HTTPException(status_code=404, detail="Room not found")
            if room.phase != "waiting":
                raise HTTPException(status_code=400, detail="Game already started")
            if len(room.seats) >= room.max_players:
                raise HTTPException(status_code=400, detail="Room is full")

            player_id = self._new_player_id()
            room.seats.append(PlayerSeat(player_id=player_id, name=player_name.strip()))
            return {"room_id": room_id, "player_id": player_id}

    def _is_finished(self, room: Room, player_index: int) -> bool:
        seat = room.seats[player_index]
        player = room.game.players[player_index]
        return seat.resolved or seat.stood or player.score > 21 or len(player.hand) >= 5

    def _move_to_next_playable(self, room: Room) -> None:
        for idx in range(len(room.seats)):
            if not self._is_finished(room, idx):
                room.current_player_index = idx
                room.phase = "player_turns"
                return
        room.phase = "dealer_turn"

    def _advance_after(self, room: Room, from_index: int) -> None:
        for idx in range(from_index + 1, len(room.seats)):
            if not self._is_finished(room, idx):
                room.current_player_index = idx
                return
        self._move_to_next_playable(room)

    def _resolve_initial_naturals(self, room: Room) -> None:
        for idx, seat in enumerate(room.seats):
            player = room.game.players[idx]
            if _is_blackjack(player) or _is_golden_blackjack(player):
                room.game.check_player(idx)
                seat.result = room.game.players[idx].result
                seat.resolved = True

    def _run_dealer_and_finalize(self, room: Room) -> None:
        game = room.game
        while len(game.dealer.hand) < 5 and game.dealer.score < 15:
            game.dealer.add_card(game.draw_card())

        for idx, seat in enumerate(room.seats):
            game.check_player(idx)
            seat.result = game.players[idx].result
            seat.resolved = True
        room.phase = "results"

    def start_game(self, room_id: str, player_id: str) -> None:
        with self.lock:
            room = self.rooms.get(room_id)
            if not room:
                raise HTTPException(status_code=404, detail="Room not found")
            if room.host_id != player_id:
                raise HTTPException(status_code=403, detail="Only host can start the game")
            if room.phase != "waiting":
                raise HTTPException(status_code=400, detail="Game already started")

            game = Game(n_players=len(room.seats))
            game.add_players()
            for idx, seat in enumerate(room.seats):
                game.players[idx].name = seat.name
            game.deal_initial_cards()
            room.game = game
            room.phase = "player_turns"
            room.current_player_index = 0
            for seat in room.seats:
                seat.stood = False
                seat.resolved = False
                seat.result = ""

            self._resolve_initial_naturals(room)
            if _is_blackjack(game.dealer) or _is_golden_blackjack(game.dealer):
                self._run_dealer_and_finalize(room)
                return
            self._move_to_next_playable(room)
            if room.phase == "dealer_turn":
                self._run_dealer_and_finalize(room)

    def player_action(self, room_id: str, player_id: str, action: str) -> None:
        with self.lock:
            room = self.rooms.get(room_id)
            if not room:
                raise HTTPException(status_code=404, detail="Room not found")
            if room.phase != "player_turns":
                raise HTTPException(status_code=400, detail="Not in player turns")

            idx = room.find_player_index(player_id)
            if idx == -1:
                raise HTTPException(status_code=403, detail="Player not in room")
            if idx != room.current_player_index:
                raise HTTPException(status_code=400, detail="Not your turn")
            if room.seats[idx].resolved:
                raise HTTPException(status_code=400, detail="Player already resolved")

            action = action.lower().strip()
            if action not in ["hit", "stand"]:
                raise HTTPException(status_code=400, detail="Action must be hit or stand")

            game = room.game
            player = game.players[idx]
            seat = room.seats[idx]

            if action == "hit":
                player.add_card(game.draw_card())
            else:
                seat.stood = True

            if self._is_finished(room, idx):
                self._advance_after(room, idx)

            if room.phase == "dealer_turn":
                self._run_dealer_and_finalize(room)

    def get_state(self, room_id: str, player_id: Optional[str]) -> RoomStateResponse:
        with self.lock:
            room = self.rooms.get(room_id)
            if not room:
                raise HTTPException(status_code=404, detail="Room not found")

            your_idx = room.find_player_index(player_id) if player_id else -1
            if your_idx < 0:
                your_idx = None

            if room.phase == "waiting":
                players = [
                    {
                        "name": seat.name,
                        "score": None,
                        "cards": [],
                        "stood": seat.stood,
                        "resolved": seat.resolved,
                    }
                    for seat in room.seats
                ]
                return RoomStateResponse(
                    room_id=room.room_id,
                    phase=room.phase,
                    current_player_index=room.current_player_index,
                    your_player_index=your_idx,
                    players=players,
                    dealer={"score": None, "cards": []},
                    can_start=(player_id == room.host_id),
                    can_act=False,
                    results=[],
                )

            game = room.game
            players = []
            for idx, seat in enumerate(room.seats):
                player = game.players[idx]
                hide = room.phase == "player_turns" and idx != room.current_player_index and not seat.resolved
                cards = []
                for card in player.hand:
                    if hide:
                        cards.append({"hidden": True})
                    else:
                        cards.append(
                            {
                                "hidden": False,
                                "rank": card.rank.value,
                                "suit": card.suit.value,
                                "image_url": _card_asset_url(card.image_path),
                            }
                        )

                players.append(
                    {
                        "name": seat.name,
                        "score": "?" if hide else player.score,
                        "cards": cards,
                        "stood": seat.stood,
                        "resolved": seat.resolved,
                        "result": seat.result,
                    }
                )

            hide_dealer = room.phase == "player_turns"
            dealer_cards = []
            for card in game.dealer.hand:
                if hide_dealer:
                    dealer_cards.append({"hidden": True})
                else:
                    dealer_cards.append(
                        {
                            "hidden": False,
                            "rank": card.rank.value,
                            "suit": card.suit.value,
                            "image_url": _card_asset_url(card.image_path),
                        }
                    )

            results = []
            if room.phase == "results":
                for seat in room.seats:
                    results.append({"name": seat.name, "result": seat.result})

            return RoomStateResponse(
                room_id=room.room_id,
                phase=room.phase,
                current_player_index=room.current_player_index,
                your_player_index=your_idx,
                players=players,
                dealer={"score": "?" if hide_dealer else game.dealer.score, "cards": dealer_cards},
                can_start=False,
                can_act=(your_idx == room.current_player_index and room.phase == "player_turns"),
                results=results,
            )


manager = RoomManager()
app = FastAPI(title="Blackjack Multiplayer API")
allowed_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173",
).split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in allowed_origins if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_asset_candidates = [
    Path(__file__).resolve().parents[3] / "assets",
    Path(__file__).resolve().parents[2] / "assets",
    Path(__file__).resolve().parents[1] / "assets",
]
ASSETS_DIR = next((p for p in _asset_candidates if p.exists()), None)
if ASSETS_DIR:
    app.mount("/assets", StaticFiles(directory=str(ASSETS_DIR)), name="assets")


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/rooms")
def create_room(payload: CreateRoomRequest):
    return manager.create_room(payload.player_name, payload.max_players)


@app.post("/rooms/{room_id}/join")
def join_room(room_id: str, payload: JoinRoomRequest):
    return manager.join_room(room_id, payload.player_name)


@app.post("/rooms/{room_id}/start")
def start_room(room_id: str, payload: StartGameRequest):
    manager.start_game(room_id, payload.player_id)
    return {"ok": True}


@app.post("/rooms/{room_id}/action")
def player_action(room_id: str, payload: ActionRequest):
    manager.player_action(room_id, payload.player_id, payload.action)
    return {"ok": True}


@app.get("/rooms/{room_id}/state")
def room_state(room_id: str, player_id: Optional[str] = None):
    return manager.get_state(room_id, player_id)
