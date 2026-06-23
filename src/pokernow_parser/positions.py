"""Table-position assignment for a hand.

Positions are derived from seat order and the button, using the standard
clockwise scheme that is independent of table size::

    BTN, SB, BB, UTG, UTG+1, UTG+2, ...

The label for each player is their offset, in seats, clockwise from the button.
Heads-up is special-cased (the button is the small blind, so the two players
are ``BTN`` and ``BB``).

The button seat is taken from the hand's declared dealer.  For the rare
"dead button" hands (where the button sits on an empty seat) it is derived from
the small/big-blind posters; in that case the button label is a best-effort
approximation while the blind labels remain exact.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from .models import Seat

UNKNOWN = "Unknown"


def _label(offset: int, num_players: int, has_small_blind: bool) -> str:
    """Map a clockwise offset from the button to a position label.

    When no small blind is posted (a "dead small blind" hand), the small-blind
    slot is empty and the big blind sits directly to the button's left, so every
    post-button position shifts up by one.
    """
    if num_players == 2:
        # Heads-up: the button posts the small blind.
        return "BTN" if offset == 0 else "BB"
    if has_small_blind:
        fixed = {0: "BTN", 1: "SB", 2: "BB"}
        first_utg_offset = 3
    else:
        fixed = {0: "BTN", 1: "BB"}
        first_utg_offset = 2
    if offset in fixed:
        return fixed[offset]
    utg_index = offset - first_utg_offset
    return "UTG" if utg_index == 0 else f"UTG+{utg_index}"


def assign_positions(
    seats: List[Seat],
    dealer: Optional[str],
    small_blind_player: Optional[str] = None,
    big_blind_player: Optional[str] = None,
) -> Dict[str, str]:
    """Return a ``{player: position_label}`` map for the seated players.

    Args:
        seats: The seats in the hand (any order; sorted internally by seat #).
        dealer: The player on the button, if known.
        small_blind_player: Player who posted the small blind (used to locate
            the button when ``dealer`` is unknown / dead-button).
        big_blind_player: Player who posted the big blind (fallback anchor).

    Returns:
        A mapping from player identifier to position label. Empty when there
        are no seats; ``"Unknown"`` for every player when the button cannot be
        located at all.
    """
    if not seats:
        return {}

    order = sorted(seats, key=lambda s: s.seat)
    names = [s.player for s in order]
    n = len(names)
    index = {name: i for i, name in enumerate(names)}

    button = _locate_button(
        index, dealer, small_blind_player, big_blind_player, n
    )
    if button is None:
        return {name: UNKNOWN for name in names}

    has_small_blind = (
        small_blind_player is not None and small_blind_player in index
    )
    return {
        name: _label((i - button) % n, n, has_small_blind)
        for i, name in enumerate(names)
    }


def _locate_button(
    index: Dict[str, int],
    dealer: Optional[str],
    small_blind_player: Optional[str],
    big_blind_player: Optional[str],
    n: int,
) -> Optional[int]:
    """Find the button's index in clockwise seat order."""
    if dealer is not None and dealer in index:
        return index[dealer]
    # Dead button: the small blind sits one seat clockwise from the button,
    # the big blind two seats.
    if small_blind_player is not None and small_blind_player in index:
        return (index[small_blind_player] - 1) % n
    if big_blind_player is not None and big_blind_player in index:
        return (index[big_blind_player] - 2) % n
    return None
