# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-06-25

First release published to PyPI.

### Added
- Table-position assignment for each hand (`Hand.positions` and
  `Hand.position_of`), using the standard `BTN / SB / BB / UTG / UTG+1 …`
  clockwise scheme. Exposed publicly as `assign_positions`.
- Handling for "dead small blind" hands (position labels shift when no small
  blind is posted) and best-effort button derivation for "dead button" hands.

### Changed
- `Seat.stack` now defaults to `0.0`.
- Modernised packaging metadata to PEP 639 (`license = "MIT"` /
  `license-files`) so the distribution passes `twine check`.

### Fixed
- Resolved a license conflict: the `LICENSE` file was GNU AGPL-3.0 while the
  README and packaging metadata declared MIT. The project is now MIT
  throughout, matching its intent as a permissively reusable library.

## [0.1.0] - 2026-06-23

### Added
- Initial release: `PokerNowParser` for parsing PokerNow CSV logs into
  `GameLog` / `Hand` / `Action` / `Seat` / `Pot` objects.
- Card parsing, chronological re-sort, run-it-twice boards, all-in detection,
  mid-hand player ID-change collapsing, and zero-sum net-result reconstruction.
- `summarize` for basic per-player and session statistics.
- Test suite with a fully sanitized sample log.

[Unreleased]: https://github.com/horris-umich/pokernow-log-parser/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/horris-umich/pokernow-log-parser/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/horris-umich/pokernow-log-parser/releases/tag/v0.1.0
