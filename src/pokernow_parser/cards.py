"""Card parsing utilities for PokerNow logs.

PokerNow renders cards with Unicode suit glyphs (``A♠``, ``10♥``).  This module
turns those tokens into lightweight :class:`Card` objects and provides helpers
to pull cards out of arbitrary log fragments (board lines, hole-card lines,
showdown lines, ...).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List

# Map the Unicode suit glyphs PokerNow uses to single-letter codes.
SUIT_GLYPH_TO_CODE = {"♠": "s", "♥": "h", "♦": "d", "♣": "c"}

# Numeric value of each rank, useful for ordering/comparison by consumers.
RANK_VALUE = {
    "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, "9": 9,
    "10": 10, "J": 11, "Q": 12, "K": 13, "A": 14,
}

# A single card token: a rank ("10" or a single char) followed by a suit glyph.
_CARD_RE = re.compile(r"(10|[2-9JQKA])([♠♥♦♣])")


@dataclass(frozen=True)
class Card:
    """An immutable playing card.

    Attributes:
        rank: The rank as written in the log (``"2"``-``"10"``, ``"J"``,
            ``"Q"``, ``"K"``, ``"A"``).
        suit: The single-letter suit code (``"s"``, ``"h"``, ``"d"``, ``"c"``).
    """

    rank: str
    suit: str

    @property
    def value(self) -> int:
        """The numeric rank value (2-14, where Ace is high)."""
        return RANK_VALUE[self.rank]

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.rank}{self.suit}"


def parse_cards(text: str) -> List[Card]:
    """Extract every card token from ``text`` in order of appearance.

    Args:
        text: Any fragment of a log line that may contain card glyphs.

    Returns:
        A list of :class:`Card` objects (possibly empty).
    """
    cards: List[Card] = []
    for rank, glyph in _CARD_RE.findall(text):
        cards.append(Card(rank=rank, suit=SUIT_GLYPH_TO_CODE[glyph]))
    return cards
