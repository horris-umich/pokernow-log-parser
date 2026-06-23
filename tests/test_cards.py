"""Tests for card parsing."""

from __future__ import annotations

from pokernow_parser import Card, parse_cards


def test_parse_single_card():
    cards = parse_cards("A♠")
    assert cards == [Card(rank="A", suit="s")]


def test_parse_ten_is_two_characters():
    # "10" must not be split into "1" and "0".
    cards = parse_cards("10♥")
    assert cards == [Card(rank="10", suit="h")]
    assert str(cards[0]) == "10h"


def test_parse_all_suits():
    cards = parse_cards("2♠ 3♥ 4♦ 5♣")
    assert [c.suit for c in cards] == ["s", "h", "d", "c"]


def test_parse_board_line_with_brackets():
    cards = parse_cards("Turn: 2♥, 9♠, Q♦ [3♣]")
    assert [str(c) for c in cards] == ["2h", "9s", "Qd", "3c"]


def test_card_value_ordering():
    assert Card("A", "s").value == 14
    assert Card("K", "h").value == 13
    assert Card("10", "d").value == 10
    assert Card("2", "c").value == 2


def test_parse_empty_returns_empty_list():
    assert parse_cards("no cards here") == []


def test_card_is_hashable():
    # frozen dataclass -> usable in sets/dicts
    assert len({Card("A", "s"), Card("A", "s")}) == 1
