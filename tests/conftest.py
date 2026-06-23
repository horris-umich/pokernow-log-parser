"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from pokernow_parser import GameLog, PokerNowParser

DATA_DIR = Path(__file__).parent / "data"
SAMPLE_CSV = DATA_DIR / "sample_session.csv"


@pytest.fixture(scope="session")
def sample_log() -> GameLog:
    """The parsed sanitized sample session shipped with the tests."""
    return PokerNowParser().parse_file(str(SAMPLE_CSV))


@pytest.fixture(scope="session")
def sample_csv_text() -> str:
    """Raw text of the sanitized sample session CSV."""
    return SAMPLE_CSV.read_text(encoding="utf-8")
