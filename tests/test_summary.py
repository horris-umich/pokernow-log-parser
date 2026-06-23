"""Tests for the summary statistics."""

from __future__ import annotations

from pokernow_parser import summarize


def test_session_level_fields(sample_log):
    s = summarize(sample_log)
    assert s.hand_count == 3
    assert s.small_blind == 5.0
    assert s.big_blind == 10.0
    assert s.started_at is not None
    assert s.ended_at is not None
    assert s.ended_at >= s.started_at


def test_net_results_sum_to_zero(sample_log):
    s = summarize(sample_log)
    assert abs(sum(p.net_result for p in s.players.values())) < 1e-9


def test_id_normalization_merges_player(sample_log):
    s = summarize(sample_log, normalize_ids=True)
    assert s.player_count == 4
    carol = s.players["Carol @ ccc999"]
    # -30 in hand 1, +120 in hand 3.
    assert carol.net_result == 90.0
    assert carol.hands_won == 1
    assert carol.hands_lost == 1


def test_without_normalization_player_splits(sample_log):
    s = summarize(sample_log, normalize_ids=False)
    assert "Carol @ ccc333" in s.players
    assert "Carol @ ccc999" in s.players


def test_per_player_counts(sample_log):
    s = summarize(sample_log)
    alice = s.players["Alice @ aaa111"]
    assert alice.net_result == 35.0
    assert alice.hands_seated == 2
    assert alice.hands_won == 1
    assert alice.total_collected == 565.0  # 65 + 500


def test_vpip(sample_log):
    s = summarize(sample_log)
    dave = s.players["Dave @ ddd444"]
    # Seated in 3 hands, voluntarily played 1 (the all-in hand 2).
    assert dave.hands_seated == 3
    assert dave.hands_voluntary == 1
    assert abs(dave.vpip - 1 / 3) < 1e-9


def test_top_winners_ordering(sample_log):
    s = summarize(sample_log)
    winners = s.top_winners(limit=2)
    assert [w.player for w in winners] == [
        "Carol @ ccc999",
        "Alice @ aaa111",
    ]


def test_biggest_win_and_loss(sample_log):
    s = summarize(sample_log)
    bob = s.players["Bob @ bbb222"]
    assert bob.biggest_loss == -120.0
    assert bob.biggest_win == 0.0
