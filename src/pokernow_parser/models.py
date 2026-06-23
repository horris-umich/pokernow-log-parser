"""Data models describing the structured contents of a PokerNow log.

The parser produces plain dataclasses so consumers can serialise, inspect, or
post-process the data however they like without depending on parser internals.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Tuple

from .cards import Card


class Street(str, Enum):
    """Betting rounds, in chronological order."""

    PREFLOP = "preflop"
    FLOP = "flop"
    TURN = "turn"
    RIVER = "river"


class ActionType(str, Enum):
    """Every kind of player action the parser recognises."""

    SMALL_BLIND = "small_blind"
    BIG_BLIND = "big_blind"
    STRADDLE = "straddle"
    ANTE = "ante"
    MISSED_BIG_BLIND = "missed_big_blind"
    MISSING_SMALL_BLIND = "missing_small_blind"
    FOLD = "fold"
    CHECK = "check"
    CALL = "call"
    BET = "bet"
    RAISE = "raise"
    SHOW = "show"


# Forced/dead money posts that are not voluntary betting actions.
BLIND_ACTIONS = frozenset(
    {
        ActionType.SMALL_BLIND,
        ActionType.BIG_BLIND,
        ActionType.STRADDLE,
        ActionType.ANTE,
        ActionType.MISSED_BIG_BLIND,
        ActionType.MISSING_SMALL_BLIND,
    }
)

# Actions that signify a player voluntarily put money in / contested the pot.
VOLUNTARY_ACTIONS = frozenset(
    {ActionType.CALL, ActionType.BET, ActionType.RAISE}
)


@dataclass
class Action:
    """A single action taken by a player within a hand.

    Attributes:
        player: The player identifier (``"Name @ id"``).
        action: The kind of action.
        street: The betting round the action happened on.
        amount: The chip amount associated with the action. For ``CALL``,
            ``BET`` and ``RAISE`` this is the *total* amount committed on the
            street ("raises to N" / "calls N"), matching PokerNow semantics.
        all_in: Whether the action put the player all in.
    """

    player: str
    action: ActionType
    street: Street
    amount: float = 0.0
    all_in: bool = False


@dataclass
class Seat:
    """A player's seat and starting stack at the beginning of a hand."""

    seat: int
    player: str
    stack: float


@dataclass
class Pot:
    """A pot (or pot fraction) collected by a player at the end of a hand.

    Attributes:
        player: The player who collected the chips.
        amount: The number of chips collected.
        hand_description: The made-hand description PokerNow prints at showdown
            (e.g. ``"Pair, 6's"``), or ``None`` when the pot was uncontested.
        second_run: ``True`` when this collection is from the second board of a
            run-it-twice pot.
    """

    player: str
    amount: float
    hand_description: Optional[str] = None
    second_run: bool = False


@dataclass
class Hand:
    """All structured information extracted for a single hand.

    The fields fall into three groups: raw header info (``number``, ``hand_id``,
    ``dealer``...), the sequence of events (``seats``, ``actions``, ``board``,
    ``pots``...), and derived results (``net_results``).
    """

    number: int
    hand_id: str
    dealer: Optional[str] = None
    dead_button: bool = False
    game_type: Optional[str] = None
    started_at: Optional[datetime] = None

    seats: List[Seat] = field(default_factory=list)
    actions: List[Action] = field(default_factory=list)

    small_blind: Optional[float] = None
    big_blind: Optional[float] = None

    # Community cards for the main board, and the second board if run twice.
    board: List[Card] = field(default_factory=list)
    board_second_run: List[Card] = field(default_factory=list)
    run_it_twice: bool = False

    # Hole cards revealed at showdown, keyed by player. ``hero_cards`` is the
    # exporting account's own hand ("Your hand is ...").
    shown_cards: Dict[str, List[Card]] = field(default_factory=dict)
    hero_cards: List[Card] = field(default_factory=list)

    pots: List[Pot] = field(default_factory=list)
    uncalled_returned: Dict[str, float] = field(default_factory=dict)

    # Player id aliases recorded mid-hand: list of (old_id, new_id).
    id_changes: List[Tuple[str, str]] = field(default_factory=list)

    ending_street: Street = Street.PREFLOP
    went_to_showdown: bool = False

    # Derived: net chip result per player for this hand (negative = loss).
    net_results: Dict[str, float] = field(default_factory=dict)

    @property
    def players(self) -> List[str]:
        """Identifiers of every player dealt into the hand (seat order)."""
        return [s.player for s in self.seats]

    def voluntary_players(self) -> set:
        """Players who called, bet or raised at any point in the hand."""
        return {
            a.player for a in self.actions if a.action in VOLUNTARY_ACTIONS
        }

    def fold_street(self, player: str) -> Optional[Street]:
        """Return the street on which ``player`` folded, or ``None``."""
        for action in self.actions:
            if action.player == player and action.action is ActionType.FOLD:
                return action.street
        return None

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return (
            f"Hand(number={self.number}, id={self.hand_id!r}, "
            f"players={len(self.seats)})"
        )


@dataclass
class GameLog:
    """The full parsed result of a PokerNow CSV log.

    Attributes:
        hands: Every hand found in the log, in chronological order.
        id_aliases: Mapping of old player identifier to the most recent
            identifier, collected from "changed the ID" lines across the log.
    """

    hands: List[Hand] = field(default_factory=list)
    id_aliases: Dict[str, str] = field(default_factory=dict)

    @property
    def players(self) -> List[str]:
        """Sorted list of all distinct player identifiers seen in any hand."""
        seen = set()
        for hand in self.hands:
            seen.update(hand.players)
        return sorted(seen)

    def __len__(self) -> int:
        return len(self.hands)

    def __iter__(self):
        return iter(self.hands)
