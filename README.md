# pokernow-log-parser

A small, dependency-free Python library that parses [PokerNow](https://www.pokernow.club/)
CSV game logs into clean, structured Python objects.

It focuses on **extraction and basic summary statistics** — turning the raw
text log into hands, actions, boards, shown cards, and per-player net results.
It deliberately does **not** do any plotting or advanced analysis, so you can
build whatever analytics you like on top of the structured data.

## Features

- Parses the full PokerNow CSV export format (the `entry`/`at`/`order` columns).
- Re-sorts the log into chronological order automatically.
- Extracts, per hand:
  - hand number, hand id, game type, dealer / dead button, timestamp
  - seats and starting stacks
  - blinds, straddles, antes, and missed/missing blinds
  - every action (fold / check / call / bet / raise / show) with street and
    all-in flag
  - community cards, including **run-it-twice** second boards
  - shown hole cards and the exporting account's own hand
  - pots collected (with showdown hand descriptions)
  - **reconstructed net chip result for every player** (verified zero-sum)
  - **table position** for every player (`BTN`, `SB`, `BB`, `UTG`, `UTG+1`, …)
- Handles mid-hand **player ID changes**, collapsing them onto one identity.
- Basic session summary: per-player net results, hands played, VPIP, wins,
  losses, folds by street, biggest win/loss, and more.
- Pure standard library — no third-party runtime dependencies.

## Installation

```bash
pip install pokernow-log-parser
```

Or, from a checkout of this repository:

```bash
pip install .
```

## Quick start

```python
from pokernow_parser import PokerNowParser, summarize

log = PokerNowParser().parse_file("my_game.csv")

print(f"{len(log)} hands, players: {log.players}")

# Inspect a single hand
hand = log.hands[0]
print(hand.number, hand.dealer, hand.board)
print(hand.net_results)        # {'Alice @ aaa111': 35.0, 'Bob @ bbb222': -5.0, ...}
print(hand.positions)          # {'Alice @ aaa111': 'BTN', 'Bob @ bbb222': 'SB', ...}
print(hand.position_of("Bob @ bbb222"))   # 'SB'

# Session summary
summary = summarize(log)
for stats in summary.top_winners():
    print(f"{stats.player:>20}  net={stats.net_result:+.0f}  vpip={stats.vpip:.0%}")
```

You can also parse directly from a string:

```python
from pokernow_parser import parse_string

log = parse_string(open("my_game.csv").read())
```

## Data model

| Object | Description |
| --- | --- |
| `GameLog` | The whole parsed log: `.hands`, `.players`, `.id_aliases`. |
| `Hand` | One hand: header info, `seats`, `actions`, `board`, `pots`, `net_results`, … |
| `Action` | A single action: `player`, `action` (`ActionType`), `street` (`Street`), `amount`, `all_in`. |
| `Seat` | A player's seat number and starting stack. |
| `Pot` | A pot/portion collected by a player, with optional showdown hand description. |
| `Card` | A parsed card with `rank`, `suit`, and numeric `value`. |
| `SessionSummary` / `PlayerStats` | Aggregated session and per-player statistics. |

### How net results are computed

Each player's net for a hand is:

```
net = chips collected + uncalled chips returned − chips committed
```

Per-street commitment follows PokerNow's "to-amount" convention: a
`call`/`bet`/`raise` *sets* the street total (it already includes any blind
posted earlier that street), while dead money (antes, missed/missing blinds) is
additive. Across every sample log this reconstruction is exactly zero-sum per
hand — a useful correctness invariant that the test suite enforces.

### Table positions

Positions are labelled clockwise from the button — `BTN`, `SB`, `BB`, `UTG`,
`UTG+1`, … — independent of table size. Heads-up is handled (the button is the
small blind), as are "dead small blind" hands (the labels shift up by one when
no small blind is posted). For the rare "dead button" hands the blind labels
remain exact while the button label is a best-effort approximation. Validated
against the sample logs, the small- and big-blind posters are labelled `SB` and
`BB` in 100% of standard hands.

## Development

```bash
pip install -e ".[dev]"
pytest                 # run the test suite
ruff check src tests   # lint
```

The tests run against a small, fully **sanitized** sample log
(`tests/data/sample_session.csv`) containing only fictional names and IDs.

## License

MIT — see [LICENSE](LICENSE).
