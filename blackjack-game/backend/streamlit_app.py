from pathlib import Path
from typing import List

import streamlit as st

from logic_game import Card, Game


_asset_candidates = [
    Path(__file__).resolve().parents[2] / "assets",
    Path(__file__).resolve().parents[1] / "assets",
    Path(__file__).resolve().parent / "assets",
]
_assets_dir = next((p for p in _asset_candidates if p.exists()), _asset_candidates[0])
BACK_IMAGE_PATH = _assets_dir / "back.png"


def init_state() -> None:
    if "game" not in st.session_state:
        st.session_state.game = None
    if "phase" not in st.session_state:
        st.session_state.phase = "setup"
    if "current_player_index" not in st.session_state:
        st.session_state.current_player_index = 0
    if "stood_players" not in st.session_state:
        st.session_state.stood_players = {}
    if "results" not in st.session_state:
        st.session_state.results = []
    if "resolved_players" not in st.session_state:
        st.session_state.resolved_players = {}


def start_new_round(n_players: int) -> None:
    game = Game(n_players)
    game.add_players()
    game.deal_initial_cards()

    st.session_state.game = game
    st.session_state.phase = "player_turns"
    st.session_state.current_player_index = 0
    st.session_state.stood_players = {idx: False for idx in range(n_players)}
    st.session_state.results = []
    st.session_state.resolved_players = {idx: False for idx in range(n_players)}
    resolve_initial_player_naturals()
    move_to_next_playable_player()


def is_finished_player(player, stood: bool) -> bool:
    return stood or player.score > 21 or len(player.hand) >= 5


def is_blackjack(player) -> bool:
    return len(player.hand) == 2 and player.score == 21


def is_golden_blackjack(player) -> bool:
    return len(player.hand) == 2 and all(card.rank.value == "A" for card in player.hand)


def is_resolved_player(player_index: int) -> bool:
    return st.session_state.resolved_players.get(player_index, False)


def is_playable_player(player_index: int) -> bool:
    game: Game = st.session_state.game
    player = game.players[player_index]
    stood = st.session_state.stood_players.get(player_index, False)
    if is_resolved_player(player_index):
        return False
    return not is_finished_player(player, stood)


def move_to_next_playable_player() -> None:
    game: Game = st.session_state.game
    for idx in range(len(game.players)):
        if is_playable_player(idx):
            st.session_state.current_player_index = idx
            st.session_state.phase = "player_turns"
            return
    st.session_state.phase = "dealer_turn"


def advance_to_next_player() -> None:
    game: Game = st.session_state.game
    n_players = len(game.players)
    current = st.session_state.current_player_index

    for next_index in range(current + 1, n_players):
        if is_playable_player(next_index):
            st.session_state.current_player_index = next_index
            return

    move_to_next_playable_player()


def render_card(card: Card, hidden: bool = False) -> None:
    if hidden:
        if BACK_IMAGE_PATH.exists():
            st.image(str(BACK_IMAGE_PATH), width=80)
        else:
            st.caption("[Hidden Card]")
        return

    image_path = Path(card.image_path)
    if image_path.exists():
        st.image(str(image_path), width=80)
    else:
        st.caption(f"{card.rank.value} of {card.suit.value}")


def render_hand(
    title: str,
    cards: List[Card],
    score,
    hide_second: bool = False,
    hide_all: bool = False,
) -> None:
    st.subheader(f"{title} (Score: {score})")
    cols = st.columns(max(len(cards), 1))
    for idx, card in enumerate(cards):
        with cols[idx]:
            hidden = hide_all or (hide_second and idx == 1)
            render_card(card, hidden=hidden)


def play_dealer_turn() -> None:
    game: Game = st.session_state.game
    while len(game.dealer.hand) < 5 and game.dealer.score < 15:
        game.dealer.add_card(game.draw_card())
    st.session_state.phase = "results"


def evaluate_results() -> None:
    game: Game = st.session_state.game
    results = []
    for idx in range(len(game.players)):
        game.check_player(idx)
        results.append((game.players[idx].name, game.players[idx].result))
    st.session_state.results = results


def has_initial_blackjack_or_golden() -> bool:
    game: Game = st.session_state.game
    if game is None:
        return False

    if is_blackjack(game.dealer) or is_golden_blackjack(game.dealer):
        return True

    for player in game.players:
        if is_blackjack(player) or is_golden_blackjack(player):
            return True
    return False


def resolve_initial_player_naturals() -> None:
    game: Game = st.session_state.game
    if game is None:
        return

    for idx, player in enumerate(game.players):
        if is_blackjack(player) or is_golden_blackjack(player):
            game.check_player(idx)
            st.session_state.resolved_players[idx] = True


def resolve_natural_blackjack() -> None:
    if st.session_state.phase != "player_turns":
        return
    game: Game = st.session_state.game
    if game is None:
        return
    if not (is_blackjack(game.dealer) or is_golden_blackjack(game.dealer)):
        return

    st.session_state.phase = "results"
    evaluate_results()


def player_controls() -> None:
    game: Game = st.session_state.game
    idx = st.session_state.current_player_index
    if is_resolved_player(idx):
        advance_to_next_player()
        st.rerun()
    player = game.players[idx]

    st.markdown(f"### Turn: {player.name}")
    col_hit, col_stand = st.columns(2)
    with col_hit:
        if st.button("Hit", use_container_width=True):
            player.add_card(game.draw_card())
            if player.score > 21 or len(player.hand) >= 5:
                advance_to_next_player()
            st.rerun()

    with col_stand:
        if st.button("Stand", use_container_width=True):
            st.session_state.stood_players[idx] = True
            advance_to_next_player()
            st.rerun()

    if is_finished_player(player, st.session_state.stood_players.get(idx, False)):
        advance_to_next_player()
        st.rerun()


def main() -> None:
    st.set_page_config(page_title="Blackjack", layout="wide")
    st.title("Blackjack Game")

    init_state()

    with st.sidebar:
        st.header("Game Setup")
        n_players = st.slider("Number of players", min_value=1, max_value=8, value=2)
        if st.button("Start New Game", use_container_width=True):
            start_new_round(n_players)
            st.rerun()

        if st.session_state.game is not None:
            if st.button("Reset Round", use_container_width=True):
                start_new_round(len(st.session_state.game.players))
                st.rerun()

    game: Game = st.session_state.game
    if game is None:
        st.info("Pick number of players and click 'Start New Game'.")
        return

    if st.session_state.phase == "player_turns":
        resolve_natural_blackjack()

    hide_dealer_all = st.session_state.phase == "player_turns"
    visible_dealer_score = "?" if hide_dealer_all else game.dealer.score
    render_hand("Dealer", game.dealer.hand, visible_dealer_score, hide_all=hide_dealer_all)

    st.divider()
    phase = st.session_state.phase
    active_player_index = st.session_state.current_player_index
    for idx, player in enumerate(game.players):
        stood = st.session_state.stood_players.get(idx, False)
        resolved = is_resolved_player(idx)
        label = " (stood)" if stood else ""
        if resolved:
            label += " (blackjack)"
        hide_player = phase == "player_turns" and idx != active_player_index and not resolved
        visible_score = "?" if hide_player else player.score
        render_hand(
            f"{player.name}{label}",
            player.hand,
            visible_score,
            hide_all=hide_player,
        )

    st.divider()
    st.write(f"Current phase: `{phase}`")

    if phase == "player_turns":
        player_controls()
    elif phase == "dealer_turn":
        if st.button("Play Dealer Turn", use_container_width=True):
            play_dealer_turn()
            st.rerun()
    elif phase == "results":
        if not st.session_state.results:
            evaluate_results()
        st.subheader("Results")
        for player_name, result in st.session_state.results:
            st.write(f"{player_name}: {result}")


if __name__ == "__main__":
    main()
