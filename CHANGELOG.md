# Changelog

All notable changes to Secret Vault are documented here.

## [1.2.0] - 2026-10-22

### Renamed

- The project is now **Secret Vault**. The repository moved from
  `kolijijani/confidential-input-form` to `kolijijani/secret-vault`, the package name, console
  script, skill name, screenshots and links all follow. The old URL redirects; the on-disk module
  (`secret_form.py`) keeps its name so imports stay stable.

## [1.1.2] - 2026-10-22

### Changed

- On desktop widths the form card now spans the same column as the header and title, instead of
  sitting 140px narrower than the header and leaving a lopsided gap on the right.

### Documentation

- The demo GIF and the README screenshot are both desktop captures now (1100x720 and 1440x1050)
  rather than a phone-shaped viewport, plus a regenerated link-preview card built from that still.

## [1.1.1] - 2026-10-22

### Added

- `CODE_OF_CONDUCT.md`, `CONTRIBUTING.md`, issue templates (bug, feature, accessibility), a pull
  request template, and `ACCESSIBILITY.md` with an honest list of known gaps.
- CI and release badges in the README; the version badge is now dynamic instead of hard-coded.

### Fixed

- Form fields are now programmatically labelled (`<label for>` → `<input id>`), including the
  `dual` paste/upload pair, so screen readers announce each field with its name.
- The "(optional)" micro-label contrast was raised above 4.5:1.
- The README screenshot showed the pre-1.1.0 footer ("expiry: after first save") and no countdown;
  it is regenerated from the current renderer.

## [1.1.0] - 2026-10-22

### Added

- `--expire-minutes` (default `15`, `0` disables): the form closes on a deadline, the page shows a
  live countdown, and an expired link returns `410 Gone` with a "This form expired" page.
- `--audit-log PATH`: one value-free line per submission (timestamp, outcome, field names, byte
  count) written mode `0600`.
- `--version`, which prints `secret-vault <version>`.
- `pyproject.toml` with a `secret-vault` console script, so `pipx`/`uvx` can install it.
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
- Secret Vault visual system and responsive one-shot form.
- Environment-file and raw-file modes.
- Atomic mode-`0600` writes with symlink protection.
- Binary-safe bounded multipart parsing and random upload names.
- Locked single-claim submission state.
- Localhost-first networking and private-network guidance.
- Linux and macOS support with POSIX permission guarantees.
- AI-agent skill, examples, security documentation, and regression tests.
