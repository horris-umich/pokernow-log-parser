"""Example: parse a PokerNow CSV log and print a basic summary.

Run it against the bundled sanitized sample::

    python examples/basic_usage.py tests/data/sample_session.csv
"""

from __future__ import annotations

import sys

from pokernow_parser import PokerNowParser, summarize


def main(path: str) -> None:
    log = PokerNowParser().parse_file(path)

    print(f"Parsed {len(log)} hands with {len(log.players)} players.\n")

    summary = summarize(log)
    if summary.big_blind:
        print(f"Stakes: {summary.small_blind}/{summary.big_blind}")
    print(f"Players: {summary.player_count}\n")

    print(f"{'Player':<24}{'Net':>10}{'Hands':>8}{'VPIP':>8}")
    print("-" * 50)
    for stats in summary.top_winners(limit=len(summary.players)):
        print(
            f"{stats.player:<24}"
            f"{stats.net_result:>10.0f}"
            f"{stats.hands_seated:>8}"
            f"{stats.vpip:>8.0%}"
        )


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    main(sys.argv[1])
