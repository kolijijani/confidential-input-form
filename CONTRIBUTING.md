# Contributing

Thanks for taking a look. This project is deliberately small: one standard-library
Python file, one skill, tests that run without dependencies.

## Ground rules

- **Standard library only.** No third-party runtime dependencies. If a change needs
  one, it needs a very good reason and a discussion issue first.
- **Never print, log, or return a secret value.** Not in errors, not in audit lines,
  not in test fixtures that get committed.
- **POSIX assumptions.** Linux and macOS only for now; do not add Windows-specific
  paths without a design discussion.
- **Keep the design fixed.** The Secret Vault theme is the constant; the JSON spec
  is the adaptive layer. Do not re-theme per task.

## Development setup

```sh
git clone https://github.com/kolijijani/secret-vault.git
cd secret-vault
python3 --version   # 3.10 or newer
```

Run the whole suite (no dependencies):

```sh
python3 -m unittest discover -s tests -v
```

Lint the way CI does:

```sh
python3 -m pip install ruff==0.17.1
ruff check scripts tests
```

Try the CLI end to end:

```sh
python3 scripts/secret_form.py --spec examples/api-key.json --bind 127.0.0.1 --expire-minutes 5
```

## Where things live

| Path | Purpose |
|---|---|
| `scripts/secret_form.py` | The whole tool: spec validation, page rendering, HTTP server, safe writes |
| `SKILL.md` | Agent-facing instructions; keep the "never break" rule intact |
| `tests/test_secret_form.py` | Unit tests: rendering, escaping, env serialisation, uploads, claim state |
| `tests/test_e2e.py` | Real-socket tests: one-shot save, `0600`, audit line, expiry, wildcard refusal |
| `install.sh` | Copies `SKILL.md` into an agent skill directory and rewrites the script path |
| `docs/agents.md` | Per-agent install matrix |

## Adding a field type

1. Accept it in `validate_spec`.
2. Render it in `render_field` (label, hint, autofocus behaviour).
3. Handle it in the POST path, both paste and upload variants.
4. Add a unit test for rendering **and** an end-to-end test for the submission.
5. Update README's field-type table and, if it is agent-relevant, `SKILL.md`.

## Pull requests

- One logical change per PR; explain the threat or usability problem it solves.
- Include tests. A behaviour change without a test will be asked for one.
- Note breaking changes explicitly in the PR description; they go in `CHANGELOG.md`
  under `### Changed`.
- Keep the CHANGELOG entry short and user-facing ("the form now expires", not
  "refactored `main()`").
- CI must be green: unit tests on 3.10–3.13, end-to-end tests, a source install of
  the CLI, and `ruff`.

## Commit messages

Imperative mood, short subject, body explaining why:

```text
feat: close the form on a deadline
fix: escape CR/LF in env values
docs: explain the per-agent install matrix
```

## Security issues

Do **not** open a public issue for a vulnerability. Follow
[`SECURITY.md`](SECURITY.md): use GitHub's private security advisory flow, and never
include real credentials in a report.
