"""Tests for less common log constructs built from inline mini-logs."""

from __future__ import annotations

from pokernow_parser import ActionType, PokerNowParser, Street


def _csv(*entries: str) -> str:
    """Build a minimal CSV (oldest-first) from raw entry strings."""
    lines = ["entry,at,order"]
    for i, entry in enumerate(entries):
        escaped = entry.replace('"', '""')
        lines.append(f'"{escaped}",2024-01-01T00:00:0{i % 10}.000Z,{i + 1}')
    return "\n".join(lines) + "\n"


def test_ante_is_committed_and_zero_sum():
    text = _csv(
        "-- starting hand #1 (id: x) (No Limit Texas Hold'em) (dealer: \"A @ a\") --",
        'Player stacks: #1 "A @ a" (100) | #2 "B @ b" (100)',
        '"A @ a" posts an ante of 1',
        '"B @ b" posts an ante of 1',
        '"A @ a" posts a small blind of 5',
        '"B @ b" posts a big blind of 10',
        '"A @ a" folds',
        'Uncalled bet of 5 returned to "B @ b"',
        '"B @ b" collected 12 from pot',
        "-- ending hand #1 --",
    )
    log = PokerNowParser().parse_string(text)
    hand = log.hands[0]
    # A: ante 1 + sb 5 = -6 ; B: ante 1 + bb 10 - 5 returned + 12 = +6
    assert hand.net_results["A @ a"] == -6.0
    assert hand.net_results["B @ b"] == 6.0
    assert abs(sum(hand.net_results.values())) < 1e-9


def test_missed_and_missing_blinds_zero_sum():
    text = _csv(
        "-- starting hand #1 (id: x) (No Limit Texas Hold'em) (dealer: \"A @ a\") --",
        'Player stacks: #1 "A @ a" (100) | #2 "B @ b" (100) | #3 "C @ c" (100)',
        '"A @ a" posts a small blind of 5',
        '"B @ b" posts a big blind of 10',
        '"C @ c" posts a missing small blind of 5',
        '"C @ c" posts a missed big blind of 10',
        '"C @ c" folds',
        '"A @ a" folds',
        'Uncalled bet of 5 returned to "B @ b"',
        '"B @ b" collected 25 from pot',
        "-- ending hand #1 --",
    )
    log = PokerNowParser().parse_string(text)
    hand = log.hands[0]
    assert abs(sum(hand.net_results.values())) < 1e-9
    # C posted 5 (missing sb, dead) + 10 (missed bb) = -15
    assert hand.net_results["C @ c"] == -15.0


def test_second_run_flop_recorded():
    text = _csv(
        "-- starting hand #1 (id: x) (No Limit Texas Hold'em) (dealer: \"A @ a\") --",
        'Player stacks: #1 "A @ a" (100) | #2 "B @ b" (100)',
        '"A @ a" posts a small blind of 5',
        '"B @ b" posts a big blind of 10',
        '"A @ a" raises to 100 and go all in',
        '"B @ b" calls 100 and go all in',
        "All players in hand choose to run it twice.",
        "Flop:  [2♥, 9♠, Q♦]",
        "Flop (second run):  [4♦, 8♥, A♥]",
        '"A @ a" collected 100 from pot',
        '"B @ b" collected 100 from pot',
        "-- ending hand #1 --",
    )
    log = PokerNowParser().parse_string(text)
    hand = log.hands[0]
    assert hand.run_it_twice is True
    assert [str(c) for c in hand.board] == ["2h", "9s", "Qd"]
    assert [str(c) for c in hand.board_second_run] == ["4d", "8h", "Ah"]


def test_malformed_timestamp_does_not_crash():
    text = (
        "entry,at,order\n"
        '"-- starting hand #1 (id: x) (No Limit Texas Hold\'em) '
        '(dealer: ""A @ a"") --",not-a-date,1\n'
        '"-- ending hand #1 --",also-bad,2\n'
    )
    log = PokerNowParser().parse_string(text)
    assert log.hands[0].started_at is None


def test_rows_without_order_column_keep_input_order():
    text = (
        "entry,at\n"
        '"-- starting hand #1 (id: x) (No Limit Texas Hold\'em) '
        '(dealer: ""A @ a"") --",2024-01-01T00:00:00.000Z\n'
        '"-- ending hand #1 --",2024-01-01T00:00:01.000Z\n'
    )
    log = PokerNowParser().parse_string(text)
    assert len(log) == 1


def test_check_action_recorded():
    text = _csv(
        "-- starting hand #1 (id: x) (No Limit Texas Hold'em) (dealer: \"A @ a\") --",
        'Player stacks: #1 "A @ a" (100) | #2 "B @ b" (100)',
        '"A @ a" posts a small blind of 5',
        '"B @ b" posts a big blind of 10',
        '"A @ a" calls 10',
        '"B @ b" checks',
        "-- ending hand #1 --",
    )
    log = PokerNowParser().parse_string(text)
    checks = [a for a in log.hands[0].actions if a.action is ActionType.CHECK]
    assert len(checks) == 1
    assert checks[0].street is Street.PREFLOP
