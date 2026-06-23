"""pokernow-log-parser: parse PokerNow CSV logs into structured Python objects.

Quick start::

    from pokernow_parser import PokerNowParser, summarize

    log = PokerNowParser().parse_file("game.csv")
    print(len(log.hands), "hands")

    summary = summarize(log)
    for stats in summary.top_winners():
        print(stats.player, stats.net_result)
"""

from __future__ import annotations

from .cards import Card, parse_cards
from .models import (
    Action,
    ActionType,
    GameLog,
    Hand,
    Pot,
    Seat,
    Street,
)
from .parser import (
    PokerNowParser,
    PokerNowParserError,
    parse_file,
    parse_string,
)
from .positions import assign_positions
from .summary import PlayerStats, SessionSummary, summarize

__version__ = "0.2.0.dev0"

__all__ = [
    "Action",
    "ActionType",
    "Card",
    "GameLog",
    "Hand",
    "PlayerStats",
    "PokerNowParser",
    "PokerNowParserError",
    "Pot",
    "Seat",
    "SessionSummary",
    "Street",
    "assign_positions",
    "parse_cards",
    "parse_file",
    "parse_string",
    "summarize",
    "__version__",
]
