"""Basic summary statistics over a parsed :class:`GameLog`.

These are intentionally lightweight aggregations (counts and chip totals) — no
charting or advanced analytics.  They give consumers a quick numerical
overview that they can build their own analysis on top of.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from .models import GameLog, Street


@dataclass
class PlayerStats:
    """Aggregated results for a single player across a session."""

    player: str
    hands_seated: int = 0          # dealt into the hand
    hands_voluntary: int = 0       # called/bet/raised at least once
    hands_won: int = 0             # net result > 0
    hands_lost: int = 0            # net result < 0
    showdowns_seen: int = 0        # was dealt in a hand that reached showdown
    net_result: float = 0.0
    total_collected: float = 0.0
    biggest_win: float = 0.0
    biggest_loss: float = 0.0
    folds_by_street: Dict[Street, int] = field(default_factory=dict)

    @property
    def vpip(self) -> float:
        """Voluntarily-put-money-in-pot rate (0.0-1.0)."""
        if self.hands_seated == 0:
            return 0.0
        return self.hands_voluntary / self.hands_seated


@dataclass
class SessionSummary:
    """High-level overview of a whole session plus per-player breakdowns."""

    hand_count: int = 0
    player_count: int = 0
    small_blind: Optional[float] = None
    big_blind: Optional[float] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    players: Dict[str, PlayerStats] = field(default_factory=dict)

    def top_winners(self, limit: int = 5) -> List[PlayerStats]:
        """Players ordered by net result, biggest winners first."""
        ranked = sorted(
            self.players.values(), key=lambda s: s.net_result, reverse=True
        )
        return ranked[:limit]


def summarize(log: GameLog, normalize_ids: bool = True) -> SessionSummary:
    """Compute a :class:`SessionSummary` from a parsed :class:`GameLog`.

    Args:
        log: The parsed game log.
        normalize_ids: When ``True`` (default), players who changed their id
            during the session (see ``log.id_aliases``) are merged onto their
            most recent identifier so their stats are not split in two.
    """
    summary = SessionSummary(hand_count=len(log.hands))

    resolve = _alias_resolver(log.id_aliases if normalize_ids else {})

    stats: Dict[str, PlayerStats] = {}

    def stats_for(player: str) -> PlayerStats:
        player = resolve(player)
        if player not in stats:
            stats[player] = PlayerStats(player=player)
        return stats[player]

    timestamps = []
    for hand in log.hands:
        if hand.started_at is not None:
            timestamps.append(hand.started_at)
        if summary.small_blind is None and hand.small_blind is not None:
            summary.small_blind = hand.small_blind
        if summary.big_blind is None and hand.big_blind is not None:
            summary.big_blind = hand.big_blind

        voluntary = {resolve(p) for p in hand.voluntary_players()}
        for seat in hand.seats:
            s = stats_for(seat.player)
            s.hands_seated += 1
            if resolve(seat.player) in voluntary:
                s.hands_voluntary += 1
            if hand.went_to_showdown:
                s.showdowns_seen += 1
            fold_street = hand.fold_street(seat.player)
            if fold_street is not None:
                s.folds_by_street[fold_street] = (
                    s.folds_by_street.get(fold_street, 0) + 1
                )

        for player, net in hand.net_results.items():
            s = stats_for(player)
            s.net_result += net
            if net > 0:
                s.hands_won += 1
                s.biggest_win = max(s.biggest_win, net)
            elif net < 0:
                s.hands_lost += 1
                s.biggest_loss = min(s.biggest_loss, net)

        for pot in hand.pots:
            stats_for(pot.player).total_collected += pot.amount

    if timestamps:
        summary.started_at = min(timestamps)
        summary.ended_at = max(timestamps)

    summary.players = stats
    summary.player_count = len(stats)
    return summary


def _alias_resolver(aliases: Dict[str, str]):
    """Build a function resolving a player id through an alias chain."""

    def resolve(player: str) -> str:
        seen = set()
        current = player
        while current in aliases and current not in seen:
            seen.add(current)
            current = aliases[current]
        return current

    return resolve
