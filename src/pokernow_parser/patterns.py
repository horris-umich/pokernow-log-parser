"""Compiled regular expressions for PokerNow log entries.

Keeping every pattern in one place makes the grammar of the log explicit and
easy to extend when PokerNow introduces new message formats.
"""

from __future__ import annotations

import re

# A quoted player token, e.g. "Alice @ aaa111".
_PLAYER = r'"([^"]+)"'

# Hand boundaries -----------------------------------------------------------
# -- starting hand #1 (id: hand0001id00)  (No Limit Texas Hold'em) (dealer: "X") --
# -- starting hand #2 (id: hand0002id00) (No Limit Texas Hold'em) (dead button) --
START_HAND = re.compile(
    r"-- starting hand #(?P<number>\d+)\s+\(id:\s*(?P<hand_id>[^)]+)\)\s*"
    r"(?:\((?P<game_type>[^)]+)\)\s*)?"
    r"\((?:dealer:\s*\"(?P<dealer>[^\"]+)\"|(?P<dead_button>dead button))\)"
)
END_HAND = re.compile(r"-- ending hand #(?P<number>\d+) --")

# Seat / stack line ---------------------------------------------------------
# Player stacks: #1 "Alice @ aaa111" (500) | #2 "Bob @ bbb222" (500)
PLAYER_STACKS_PREFIX = "Player stacks:"
SEAT_ENTRY = re.compile(rf"#(\d+)\s+{_PLAYER}\s*\((\d+(?:\.\d+)?)\)")

# Forced posts --------------------------------------------------------------
SMALL_BLIND = re.compile(rf"{_PLAYER} posts a small blind of (\d+(?:\.\d+)?)")
BIG_BLIND = re.compile(rf"{_PLAYER} posts a big blind of (\d+(?:\.\d+)?)")
STRADDLE = re.compile(rf"{_PLAYER} posts a straddle of (\d+(?:\.\d+)?)")
ANTE = re.compile(rf"{_PLAYER} posts an ante of (\d+(?:\.\d+)?)")
MISSED_BIG_BLIND = re.compile(
    rf"{_PLAYER} posts a missed big blind of (\d+(?:\.\d+)?)"
)
MISSING_SMALL_BLIND = re.compile(
    rf"{_PLAYER} posts a missing small blind of (\d+(?:\.\d+)?)"
)

# Voluntary actions ---------------------------------------------------------
# An optional " and go all in" suffix may follow the amount.
_ALL_IN = r"(?P<all_in> and go all in)?"
FOLD = re.compile(rf"{_PLAYER} folds")
CHECK = re.compile(rf"{_PLAYER} checks")
CALL = re.compile(rf"{_PLAYER} calls (\d+(?:\.\d+)?){_ALL_IN}")
BET = re.compile(rf"{_PLAYER} bets (\d+(?:\.\d+)?){_ALL_IN}")
RAISE = re.compile(rf"{_PLAYER} raises to (\d+(?:\.\d+)?){_ALL_IN}")

# Showdown / results --------------------------------------------------------
SHOWS = re.compile(rf"{_PLAYER} shows a (.+?)\.?$")
HERO_HAND = re.compile(r"Your hand is (.+)")
COLLECTED = re.compile(
    rf"{_PLAYER} collected (\d+(?:\.\d+)?) from pot"
    r"(?: with (?P<desc>.+?))?(?P<second_run> on the second run)?"
    r"(?: \(combination: [^)]+\))?$"
)
UNCALLED = re.compile(
    rf"Uncalled bet of (\d+(?:\.\d+)?) returned to {_PLAYER}"
)

# Board lines ---------------------------------------------------------------
# "Flop:  [J♥, 6♣, 7♣]" / "Turn: J♥, 6♣, 7♣ [10♦]" / "River: ... [4♣]"
FLOP = re.compile(r"Flop(?P<second_run> \(second run\))?:")
TURN = re.compile(r"Turn(?P<second_run> \(second run\))?:")
RIVER = re.compile(r"River(?P<second_run> \(second run\))?:")

# Session / table events ----------------------------------------------------
ID_CHANGE = re.compile(
    rf"The player {_PLAYER} changed the ID from (\w+) to (\w+)"
)
RUN_IT_TWICE = re.compile(r"run it twice", re.IGNORECASE)
