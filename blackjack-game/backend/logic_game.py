import random
import importlib.util
from pathlib import Path
from typing import List

_enum_path = Path(__file__).resolve().with_name("enum.py")
_enum_spec = importlib.util.spec_from_file_location("card_enum", _enum_path)
_enum_module = importlib.util.module_from_spec(_enum_spec)
_enum_spec.loader.exec_module(_enum_module)
Rank = _enum_module.Rank
Suit = _enum_module.Suit

ASSETS_DIR = Path(__file__).resolve().parents[2] / "assets"
RANK_TO_ASSET_NAME = {
    Rank.ACE: "ace",
    Rank.JACK: "jack",
    Rank.QUEEN: "queen",
    Rank.KING: "king",
}

_asset_candidates = [
    Path(__file__).resolve().parents[2] / "assets",
    Path(__file__).resolve().parents[1] / "assets",
    Path(__file__).resolve().parent / "assets",
]
for _candidate in _asset_candidates:
    if _candidate.exists():
        ASSETS_DIR = _candidate
        break


class Card:
    def __init__(self, suit: Suit, rank: Rank):
        self.suit = suit
        self.rank = rank
        self.image_path = str(ASSETS_DIR / self._image_filename())

    def _image_filename(self) -> str:
        rank_name = RANK_TO_ASSET_NAME.get(self.rank, self.rank.value)
        suit_name = self.suit.value.lower()
        return f"{rank_name}_of_{suit_name}.png"

    def __repr__(self):
        return f"{self.rank.value} of {self.suit.value}"


class Player:
    def __init__(self, name: str, is_dealer: bool):
        self.name = name
        self.hand: List[Card] = []
        self.score = 0
        self.is_dealer = is_dealer
        self.result = ""

    def add_card(self, card: Card):
        self.hand.append(card)
        self.calculate_score()

    def calculate_score(self):
        base_score = 0
        num_aces = 0

        for card in self.hand:
            if card.rank in [Rank.JACK, Rank.QUEEN, Rank.KING]:
                base_score += 10
            elif card.rank == Rank.ACE:
                num_aces += 1
            else:
                base_score += int(card.rank.value)

        possible_scores = []

        def generate_scores(current_total: int, ace_index: int):
            if ace_index == num_aces:
                possible_scores.append(current_total)
                return
            for ace_value in [1, 10, 11]:
                generate_scores(current_total + ace_value, ace_index + 1)

        generate_scores(base_score, 0)

        threshold = 15 if self.is_dealer else 16
        valid_scores = [score for score in possible_scores if threshold <= score <= 21]

        if valid_scores:
            self.score = max(valid_scores)
            return

        fallback_scores = [score for score in possible_scores if score <= 21]
        self.score = max(fallback_scores) if fallback_scores else min(possible_scores)

    def reset_hand(self):
        self.hand.clear()
        self.score = 0


class Game:
    def __init__(self, n_players: int):
        self.n_players = n_players
        if n_players < 1:
            raise ValueError("Number of players must be at least 1")
        if n_players > 8:
            raise ValueError("Number of players cannot exceed 8")

        self.players: List[Player] = []
        self.dealer = Player("Dealer", is_dealer=True)
        self.deck = self.create_deck()

    def create_deck(self):
        deck = [Card(suit, rank) for suit in Suit for rank in Rank]
        random.shuffle(deck)
        return deck

    def draw_card(self) -> Card:
        if not self.deck:
            self.deck = self.create_deck()
        return self.deck.pop()

    def add_players(self):
        for i in range(self.n_players):
            player_name = f"Player {i + 1}"
            self.players.append(Player(player_name, is_dealer=False))

    def deal_initial_cards(self):
        for _ in range(2):
            for player in self.players:
                player.add_card(self.draw_card())
            self.dealer.add_card(self.draw_card())

    def reset_game(self):
        self.deck = self.create_deck()
        self.dealer.reset_hand()
        for player in self.players:
            player.reset_hand()

    def play_turn(self):
        for player in self.players:
            while len(player.hand) < 5 and player.score < 16:
                want_card = input(f"{player.name}, do you want another card? (y/n): ").strip().lower()

                if want_card == "n":
                    break
                if want_card == "y":
                    player.add_card(self.draw_card())

        while len(self.dealer.hand) < 5 and self.dealer.score < 15:
            want_check = input("Do you want to check players? (y/n): ").strip().lower()
            if want_check == "n":
                want_card = input("Do you want another card? (y/n): ").strip().lower()
                if want_card == "n":
                    break
                if want_card == "y":
                    self.dealer.add_card(self.draw_card())
            elif want_check == "y":
                who = int(input("Which player do you want to check? (enter the index of the player): ").strip())
                self.check_player(who)

    def check_player(self, player_index: int):
        if player_index < 0 or player_index >= len(self.players):
            raise ValueError(f"Player index {player_index} is out of range.")
        result = self.evaluate_winner(player_index)
        self.players[player_index].result = result

    def evaluate_winner(self, player_index: int):
        dealer = self.dealer

        def is_blackjack(player: Player):
            return len(player.hand) == 2 and player.score == 21

        def is_golden_blackjack(player: Player):
            return len(player.hand) == 2 and all(card.rank == Rank.ACE for card in player.hand)

        def is_spirit(player: Player):
            return len(player.hand) == 5 and player.score <= 21

        player = self.players[player_index]
        player_score = player.score
        dealer_score = dealer.score

        player_golden = is_golden_blackjack(player)
        dealer_golden = is_golden_blackjack(dealer)
        player_blackjack = is_blackjack(player)
        dealer_blackjack = is_blackjack(dealer)

        # Priority: Golden Blackjack > Blackjack
        if player_golden and dealer_golden:
            return "Draw (both Golden Blackjack)"
        if player_golden:
            return "Player wins with Golden Blackjack"
        if dealer_golden:
            return "Dealer wins with Golden Blackjack"

        if player_blackjack and dealer_blackjack:
            return "Draw (both Blackjack)"
        if dealer_blackjack:
            return "Dealer wins with Blackjack"
        if player_blackjack:
            return "Player wins with Blackjack"

        if is_spirit(player) and is_spirit(dealer):
            return "Draw (both Di Linh)"
        if is_spirit(player):
            return "Player wins with Di Linh"
        if is_spirit(dealer):
            return "Dealer wins with Di Linh"

        if player_score > 21:
            return "Player busted - Dealer wins"
        if dealer_score > 21:
            return "Dealer busted - Player wins"
        if player_score > dealer_score:
            return "Player wins"
        if player_score < dealer_score:
            return "Dealer wins"
        return "Draw"
