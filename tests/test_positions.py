"""Tests for table-position assignment."""

from __future__ import annotations

from pokernow_parser import Seat, assign_positions


def _seats(*players):
    """Build seats numbered 1..n in the given player order."""
    return [Seat(seat=i + 1, player=p) for i, p in enumerate(players)]


def test_six_handed_full_ring():
    seats = _seats("A", "B", "C", "D", "E", "F")
    pos = assign_positions(seats, dealer="A", small_blind_player="B",
                           big_blind_player="C")
    assert pos == {
        "A": "BTN",
        "B": "SB",
        "C": "BB",
        "D": "UTG",
        "E": "UTG+1",
        "F": "UTG+2",
    }


def test_button_not_first_seat_wraps_around():
    seats = _seats("A", "B", "C", "D")
    # Dealer is C; SB=D, BB=A, UTG=B.
    pos = assign_positions(seats, dealer="C", small_blind_player="D",
                           big_blind_player="A")
    assert pos == {"C": "BTN", "D": "SB", "A": "BB", "B": "UTG"}


def test_heads_up_button_is_small_blind():
    seats = _seats("A", "B")
    pos = assign_positions(seats, dealer="A", small_blind_player="A",
                           big_blind_player="B")
    assert pos == {"A": "BTN", "B": "BB"}


def test_three_handed():
    seats = _seats("A", "B", "C")
    pos = assign_positions(seats, dealer="A", small_blind_player="B",
                           big_blind_player="C")
    assert pos == {"A": "BTN", "B": "SB", "C": "BB"}


def test_dead_small_blind_shifts_positions():
    # No small blind posted: BB sits directly left of the button.
    seats = _seats("A", "B", "C", "D")
    pos = assign_positions(seats, dealer="A", small_blind_player=None,
                           big_blind_player="B")
    assert pos == {"A": "BTN", "B": "BB", "C": "UTG", "D": "UTG+1"}


def test_dead_button_derives_from_small_blind():
    # Dealer unknown; SB poster locates the button (one seat back).
    seats = _seats("A", "B", "C")
    pos = assign_positions(seats, dealer=None, small_blind_player="B",
                           big_blind_player="C")
    assert pos["B"] == "SB"
    assert pos["C"] == "BB"
    assert pos["A"] == "BTN"


def test_unknown_button_returns_unknown():
    seats = _seats("A", "B", "C")
    pos = assign_positions(seats, dealer=None, small_blind_player=None,
                           big_blind_player=None)
    assert set(pos.values()) == {"Unknown"}


def test_empty_seats():
    assert assign_positions([], dealer=None) == {}


# -- integration with the parser ------------------------------------------

def test_positions_on_sample_hand(sample_log):
    pos = sample_log.hands[0].positions
    assert pos["Alice @ aaa111"] == "BTN"
    assert pos["Bob @ bbb222"] == "SB"
    assert pos["Carol @ ccc333"] == "BB"
    assert pos["Dave @ ddd444"] == "UTG"


def test_position_of_helper(sample_log):
    hand = sample_log.hands[0]
    assert hand.position_of("Dave @ ddd444") == "UTG"
    assert hand.position_of("nobody") is None


def test_positions_heads_up_hand(sample_log):
    pos = sample_log.hands[1].positions
    assert pos == {"Alice @ aaa111": "BTN", "Dave @ ddd444": "BB"}


def test_positions_dead_button_hand(sample_log):
    pos = sample_log.hands[2].positions
    # Blind labels are exact even for a dead button.
    assert pos["Bob @ bbb222"] == "SB"
    assert pos["Carol @ ccc333"] == "BB"
