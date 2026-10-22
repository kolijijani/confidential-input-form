# Changelog

All notable changes to Terminal Vault are documented here.

## [1.1.0] - 2026-10-22

### Added

- `--expire-minutes` (default `15`, `0` disables): the form closes on a deadline, the page shows a
  live countdown, and an expired link returns `410 Gone` with a "This form expired" page.
- `--audit-log PATH`: one value-free line per submission (timestamp, outcome, field names, byte
  count) written mode `0600`.
- `--version`, which prints `confidential-input-form <version>`.
- `pyproject.toml` with a `confidential-input-form` console script, so `pipx`/`uvx` can install it.
- `install.sh` plus `docs/agents.md` covering Hermes, Claude Code, Codex and Cursor skill paths, and
  the script-path rewrite that makes a copied `SKILL.md` actually work.
- Real-socket end-to-end tests: one-shot save, `0600` target, audit line without values, refusal
  after expiry, wildcard-bind rejection.

### Changed

- **Breaking:** `--bind 0.0.0.0` now exits with an error unless `--allow-wildcard` is passed.
- The page footer reads `single use` instead of the misleading `expiry: after first save`.
- CI runs unit tests, end-to-end tests, a source install of the CLI, `ruff`, and `sh -n install.sh`.

### Fixed

- An abandoned form no longer stays listening forever: the deadline closes it and writes nothing.

## [1.0.0] - 2026-10-21

### Added

- Adaptive JSON specifications with six field types.
- Terminal Vault visual system and responsive one-shot form.
- Environment-file and raw-file modes.
- Atomic mode-`0600` writes with symlink protection.
- Binary-safe bounded multipart parsing and random upload names.
- Locked single-claim submission state.
- Localhost-first networking and private-network guidance.
- Linux and macOS support with POSIX permission guarantees.
- AI-agent skill, examples, security documentation, and regression tests.
