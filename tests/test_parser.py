"""Tests for the PokerNow log parser."""

from __future__ import annotations

import pytest

from pokernow_parser import (
    ActionType,
    PokerNowParser,
    PokerNowParserError,
    Street,
    parse_string,
)


def test_parses_expected_hand_count(sample_log):
    assert len(sample_log) == 3
    assert [h.number for h in sample_log] == [1, 2, 3]


def test_rows_are_sorted_chronologically(sample_log):
    # The fixture is stored newest-first; hands must come out oldest-first.
    assert sample_log.hands[0].hand_id == "hand0001id00"
    assert sample_log.hands[-1].hand_id == "hand0003id00"


def test_players_collected(sample_log):
    assert sample_log.players == [
        "Alice @ aaa111",
        "Bob @ bbb222",
        "Carol @ ccc333",
        "Dave @ ddd444",
    ]


def test_header_fields(sample_log):
    hand = sample_log.hands[0]
    assert hand.dealer == "Alice @ aaa111"
    assert hand.dead_button is False
    assert hand.game_type == "No Limit Texas Hold'em"
    assert hand.started_at is not None


def test_seats_and_stacks(sample_log):
    seats = sample_log.hands[0].seats
    assert [s.seat for s in seats] == [1, 2, 3, 4]
    assert seats[0].player == "Alice @ aaa111"
    assert seats[0].stack == 1000.0


def test_blinds_detected(sample_log):
    hand = sample_log.hands[0]
    assert hand.small_blind == 5.0
    assert hand.big_blind == 10.0


def test_hero_cards(sample_log):
    assert [str(c) for c in sample_log.hands[0].hero_cards] == ["As", "Kd"]


def test_board_extraction(sample_log):
    hand = sample_log.hands[1]
    assert [str(c) for c in hand.board] == ["2h", "9s", "Qd", "3c", "Jh"]


def test_action_sequence_and_streets(sample_log):
    hand = sample_log.hands[0]
    kinds = [(a.player, a.action, a.street) for a in hand.actions]
    assert (
        "Alice @ aaa111",
        ActionType.RAISE,
        Street.PREFLOP,
    ) in kinds
    assert (
        "Alice @ aaa111",
        ActionType.BET,
        Street.FLOP,
    ) in kinds
    # Carol folds on the flop.
    assert hand.fold_street("Carol @ ccc333") is Street.FLOP


def test_uncalled_bet_returned(sample_log):
    hand = sample_log.hands[0]
    assert hand.uncalled_returned == {"Alice @ aaa111": 40.0}


def test_net_results_hand1(sample_log):
    net = sample_log.hands[0].net_results
    assert net["Alice @ aaa111"] == 35.0
    assert net["Carol @ ccc333"] == -30.0
    assert net["Bob @ bbb222"] == -5.0


@pytest.mark.parametrize("hand_index", [0, 1, 2])
def test_each_hand_is_zero_sum(sample_log, hand_index):
    net = sample_log.hands[hand_index].net_results
    assert abs(sum(net.values())) < 1e-9


def test_all_in_flag_parsed(sample_log):
    hand = sample_log.hands[1]
    all_in_actions = [a for a in hand.actions if a.all_in]
    assert len(all_in_actions) == 2
    assert all(a.amount == 500.0 for a in all_in_actions)


def test_run_it_twice(sample_log):
    hand = sample_log.hands[1]
    assert hand.run_it_twice is True
    assert [str(c) for c in hand.board_second_run] == [
        "4d",
        "8h",
        "Ah",
        "10s",
        "5c",
    ]
    # Split pot: each player nets zero.
    assert hand.net_results["Alice @ aaa111"] == 0.0
    assert hand.net_results["Dave @ ddd444"] == 0.0


def test_showdown_and_shown_cards(sample_log):
    hand = sample_log.hands[1]
    assert hand.went_to_showdown is True
    assert [str(c) for c in hand.shown_cards["Dave @ ddd444"]] == ["Qh", "Qs"]


def test_dead_button(sample_log):
    hand = sample_log.hands[2]
    assert hand.dead_button is True
    assert hand.dealer is None


def test_mid_hand_id_change_collapses_player(sample_log):
    hand = sample_log.hands[2]
    # Old id should not survive into net results...
    assert "Carol @ ccc333" not in hand.net_results
    # ...the BB posted under the old id is merged into the new id's commitment.
    assert hand.net_results["Carol @ ccc999"] == 120.0
    assert hand.net_results["Bob @ bbb222"] == -120.0
    assert ("Carol @ ccc333", "Carol @ ccc999") in hand.id_changes


def test_id_aliases_recorded_on_log(sample_log):
    assert sample_log.id_aliases == {"Carol @ ccc333": "Carol @ ccc999"}


def test_pot_hand_description(sample_log):
    pots = sample_log.hands[2].pots
    assert pots[0].player == "Carol @ ccc999"
    assert pots[0].amount == 240.0
    assert pots[0].hand_description == "Pair, K's"


def test_parse_string_equivalent_to_file(sample_log, sample_csv_text):
    log = parse_string(sample_csv_text)
    assert len(log) == len(sample_log)


def test_missing_entry_column_raises():
    with pytest.raises(PokerNowParserError):
        PokerNowParser().parse_string("wrong,columns\n1,2\n")


def test_empty_log_is_handled():
    log = PokerNowParser().parse_string("entry,at,order\n")
    assert len(log) == 0
    assert log.players == []


def test_truncated_hand_without_end_is_kept():
    text = (
        "entry,at,order\n"
        '"-- starting hand #9 (id: zzz) (No Limit Texas Hold\'em) '
        '(dealer: ""A @ a"") --",2024-01-01T00:00:00.000Z,1\n'
        '"""A @ a"" posts a small blind of 5",2024-01-01T00:00:01.000Z,2\n'
    )
    log = PokerNowParser().parse_string(text)
    assert len(log) == 1
    assert log.hands[0].number == 9
