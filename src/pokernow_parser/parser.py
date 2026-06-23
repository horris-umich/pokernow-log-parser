"""The PokerNow log parser.

:class:`PokerNowParser` turns a PokerNow CSV export (or its raw rows) into a
:class:`~pokernow_parser.models.GameLog` of structured :class:`Hand` objects.

Usage::

    from pokernow_parser import PokerNowParser

    log = PokerNowParser().parse_file("my_game.csv")
    for hand in log.hands:
        print(hand.number, hand.net_results)
"""

from __future__ import annotations

import csv
from collections import defaultdict
from datetime import datetime
from typing import Dict, Iterable, List, Optional

from . import patterns as P
from .cards import parse_cards
from .models import (
    Action,
    ActionType,
    GameLog,
    Hand,
    Pot,
    Seat,
    Street,
)

# Columns expected in a PokerNow CSV export.
_ENTRY_COL = "entry"
_AT_COL = "at"
_ORDER_COL = "order"


class PokerNowParserError(Exception):
    """Raised when a log cannot be parsed (e.g. missing required columns)."""


class PokerNowParser:
    """Parse PokerNow logs into structured data.

    The parser is stateless between calls; a single instance may be reused to
    parse many logs.
    """

    # -- public API --------------------------------------------------------

    def parse_file(self, path: str, encoding: str = "utf-8") -> GameLog:
        """Parse a PokerNow CSV export from a file path."""
        with open(path, "r", encoding=encoding, newline="") as handle:
            return self.parse_csv(handle)

    def parse_string(self, text: str) -> GameLog:
        """Parse a PokerNow CSV export held in a string."""
        import io

        return self.parse_csv(io.StringIO(text))

    def parse_csv(self, handle: Iterable[str]) -> GameLog:
        """Parse from any iterable of CSV lines (e.g. an open file)."""
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or _ENTRY_COL not in reader.fieldnames:
            raise PokerNowParserError(
                "CSV is missing the required 'entry' column; is this a "
                "PokerNow log export?"
            )
        return self.parse_rows(reader)

    def parse_rows(self, rows: Iterable[Dict[str, str]]) -> GameLog:
        """Parse from an iterable of row dicts with 'entry'/'at'/'order' keys.

        Rows are sorted into chronological order using the ``order`` column
        (PokerNow exports newest-first), falling back to input order when the
        column is absent.
        """
        materialised = list(rows)

        def sort_key(row: Dict[str, str]):
            raw = row.get(_ORDER_COL)
            try:
                return (0, int(raw))
            except (TypeError, ValueError):
                return (1, 0)

        if all(_ORDER_COL in row for row in materialised):
            materialised.sort(key=sort_key)

        return self._parse_ordered(materialised)

    # -- internals ---------------------------------------------------------

    def _parse_ordered(self, rows: List[Dict[str, str]]) -> GameLog:
        log = GameLog()
        hand: Optional[Hand] = None
        street = Street.PREFLOP

        for row in rows:
            entry = (row.get(_ENTRY_COL) or "").strip()
            if not entry:
                continue

            # New hand starts.
            start = P.START_HAND.search(entry)
            if start:
                hand = self._begin_hand(start, row)
                street = Street.PREFLOP
                continue

            if hand is None:
                # Lines between hands (joins, admin actions). We still capture
                # global id changes so aliases are complete.
                self._capture_id_change(entry, log)
                continue

            # Hand end: finalise and store.
            end = P.END_HAND.search(entry)
            if end:
                self._finalize_hand(hand)
                log.hands.append(hand)
                hand = None
                street = Street.PREFLOP
                continue

            street = self._consume_line(entry, row, hand, street, log)

        # A truncated log may end mid-hand; keep what we have.
        if hand is not None:
            self._finalize_hand(hand)
            log.hands.append(hand)

        return log

    def _begin_hand(self, match, row: Dict[str, str]) -> Hand:
        return Hand(
            number=int(match.group("number")),
            hand_id=match.group("hand_id").strip(),
            dealer=match.group("dealer"),
            dead_button=bool(match.group("dead_button")),
            game_type=match.group("game_type"),
            started_at=_parse_timestamp(row.get(_AT_COL)),
        )

    def _consume_line(
        self,
        entry: str,
        row: Dict[str, str],
        hand: Hand,
        street: Street,
        log: GameLog,
    ) -> Street:
        """Process one in-hand line; returns the (possibly updated) street."""

        # Seat / stack snapshot.
        if entry.startswith(P.PLAYER_STACKS_PREFIX):
            for seat_no, player, stack in P.SEAT_ENTRY.findall(entry):
                hand.seats.append(
                    Seat(seat=int(seat_no), player=player, stack=float(stack))
                )
            return street

        # Board transitions (main run updates current street).
        if entry.startswith("Flop"):
            return self._consume_board(entry, hand, Street.FLOP, P.FLOP, street)
        if entry.startswith("Turn"):
            return self._consume_board(entry, hand, Street.TURN, P.TURN, street)
        if entry.startswith("River"):
            return self._consume_board(
                entry, hand, Street.RIVER, P.RIVER, street
            )

        # Forced posts.
        for pattern, action_type, set_blind in (
            (P.SMALL_BLIND, ActionType.SMALL_BLIND, "small"),
            (P.BIG_BLIND, ActionType.BIG_BLIND, "big"),
            (P.STRADDLE, ActionType.STRADDLE, None),
            (P.ANTE, ActionType.ANTE, None),
            (P.MISSED_BIG_BLIND, ActionType.MISSED_BIG_BLIND, None),
            (P.MISSING_SMALL_BLIND, ActionType.MISSING_SMALL_BLIND, None),
        ):
            m = pattern.search(entry)
            if m:
                amount = float(m.group(2))
                hand.actions.append(
                    Action(m.group(1), action_type, street, amount)
                )
                if set_blind == "small":
                    hand.small_blind = amount
                elif set_blind == "big":
                    hand.big_blind = amount
                return street

        # Voluntary actions.
        m = P.FOLD.search(entry)
        if m:
            hand.actions.append(Action(m.group(1), ActionType.FOLD, street))
            return street
        m = P.CHECK.search(entry)
        if m:
            hand.actions.append(Action(m.group(1), ActionType.CHECK, street))
            return street
        for pattern, action_type in (
            (P.RAISE, ActionType.RAISE),
            (P.BET, ActionType.BET),
            (P.CALL, ActionType.CALL),
        ):
            m = pattern.search(entry)
            if m:
                hand.actions.append(
                    Action(
                        player=m.group(1),
                        action=action_type,
                        street=street,
                        amount=float(m.group(2)),
                        all_in=bool(m.group("all_in")),
                    )
                )
                return street

        # Hole cards.
        m = P.SHOWS.search(entry)
        if m:
            cards = parse_cards(m.group(2))
            if cards:
                hand.shown_cards[m.group(1)] = cards
                hand.actions.append(Action(m.group(1), ActionType.SHOW, street))
            return street
        m = P.HERO_HAND.search(entry)
        if m:
            hand.hero_cards = parse_cards(m.group(1))
            return street

        # Pot results.
        m = P.COLLECTED.search(entry)
        if m:
            desc = m.group("desc")
            second_run = bool(m.group("second_run"))
            hand.pots.append(
                Pot(
                    player=m.group(1),
                    amount=float(m.group(2)),
                    hand_description=desc.strip() if desc else None,
                    second_run=second_run,
                )
            )
            if desc:
                hand.went_to_showdown = True
            hand.ending_street = street
            return street
        m = P.UNCALLED.search(entry)
        if m:
            amount = float(m.group(1))
            player = m.group(2)
            hand.uncalled_returned[player] = (
                hand.uncalled_returned.get(player, 0.0) + amount
            )
            return street

        # Run-it-twice marker.
        if P.RUN_IT_TWICE.search(entry):
            hand.run_it_twice = True
            return street

        # Mid-hand id change.
        self._capture_id_change(entry, log, hand)
        return street

    def _consume_board(
        self,
        entry: str,
        hand: Hand,
        new_street: Street,
        pattern,
        street: Street,
    ) -> Street:
        m = pattern.match(entry)
        second_run = bool(m and m.group("second_run"))
        cards = parse_cards(entry)
        if second_run:
            hand.board_second_run = cards
            hand.run_it_twice = True
            return street  # second board does not advance the action street
        hand.board = cards
        return new_street

    def _capture_id_change(
        self, entry: str, log: GameLog, hand: Optional[Hand] = None
    ) -> None:
        m = P.ID_CHANGE.search(entry)
        if not m:
            return
        name, old_id, new_id = m.group(1), m.group(2), m.group(3)
        # The quoted name already carries the *new* id; reconstruct the old one.
        base = name.rsplit("@", 1)[0].strip()
        old_identifier = f"{base} @ {old_id}"
        new_identifier = f"{base} @ {new_id}"
        log.id_aliases[old_identifier] = new_identifier
        if hand is not None:
            hand.id_changes.append((old_identifier, new_identifier))

    def _finalize_hand(self, hand: Hand) -> None:
        """Reconstruct each player's net chip result for the hand.

        Net result = chips collected + uncalled chips returned - chips
        committed.  Per-street commitment uses the PokerNow "to-amount"
        convention: a call/bet/raise *sets* the street total (it already
        includes any blind posted earlier on that street), while dead posts
        (antes, missed/missing blinds) are additive.

        Players who change their id mid-hand are collapsed onto their final
        identifier so a blind posted under the old id and a raise under the new
        id are treated as a single player's commitment.
        """
        canon = _build_canonical_map(hand)

        committed: Dict[str, Dict[Street, float]] = defaultdict(
            lambda: defaultdict(float)
        )
        # Dead money (antes) is never part of a live "to-amount", so it is kept
        # separate and always additive.
        dead_money: Dict[str, float] = defaultdict(float)
        # Track dead "missing small blind" chips that must be re-added on top
        # of a later preflop to-amount (the call/raise total excludes them).
        missing_sb: Dict[str, float] = defaultdict(float)

        for action in hand.actions:
            p = canon(action.player)
            if action.action in (
                ActionType.SMALL_BLIND,
                ActionType.BIG_BLIND,
                ActionType.STRADDLE,
            ):
                committed[p][Street.PREFLOP] = action.amount
            elif action.action is ActionType.ANTE:
                dead_money[p] += action.amount
            elif action.action is ActionType.MISSED_BIG_BLIND:
                committed[p][Street.PREFLOP] += action.amount
            elif action.action is ActionType.MISSING_SMALL_BLIND:
                committed[p][Street.PREFLOP] += action.amount
                missing_sb[p] = action.amount
            elif action.action in (
                ActionType.CALL,
                ActionType.BET,
                ActionType.RAISE,
            ):
                if action.street is Street.PREFLOP:
                    committed[p][Street.PREFLOP] = action.amount + missing_sb[p]
                else:
                    committed[p][action.street] = action.amount

        net: Dict[str, float] = defaultdict(float)
        for player, by_street in committed.items():
            net[player] -= sum(by_street.values())
        for player, amount in dead_money.items():
            net[player] -= amount
        for player, amount in hand.uncalled_returned.items():
            net[canon(player)] += amount
        for pot in hand.pots:
            net[canon(pot.player)] += pot.amount

        # Normalise -0.0 to 0.0 and drop nothing; keep all involved players.
        hand.net_results = {p: (v + 0.0) for p, v in net.items()}


def parse_file(path: str, encoding: str = "utf-8") -> GameLog:
    """Convenience wrapper around :meth:`PokerNowParser.parse_file`."""
    return PokerNowParser().parse_file(path, encoding=encoding)


def parse_string(text: str) -> GameLog:
    """Convenience wrapper around :meth:`PokerNowParser.parse_string`."""
    return PokerNowParser().parse_string(text)


def _build_canonical_map(hand: Hand):
    """Return a function mapping any player id to its final id for this hand.

    Resolves chains of mid-hand id changes (old -> new -> newer) so every
    alias points at the most recent identifier.
    """
    direct = dict(hand.id_changes)  # old -> new

    def canon(player: str) -> str:
        seen = set()
        current = player
        while current in direct and current not in seen:
            seen.add(current)
            current = direct[current]
        return current

    return canon


def _parse_timestamp(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None
