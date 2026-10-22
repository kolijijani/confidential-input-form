# Using the skill with an AI agent

`SKILL.md` is the agent-facing instruction file. `scripts/secret_form.py` is the tool it calls.
Installing the skill does **not** install the script — the skill always points at a real path, so
either keep the checkout or install the CLI and point the skill at that command.

## Skill directory per agent

| Agent | Skill directory | Notes |
|---|---|---|
| Hermes | `~/.hermes/skills/secret-vault/SKILL.md` | `hermes skills install <raw SKILL.md URL>` also works, but the script path still needs fixing |
| Claude Code | `~/.claude/skills/secret-vault/SKILL.md` | Skills load by `name` + `description` frontmatter |
| Codex / generic agent | `~/.agents/skills/` or a project `.agents/skills/` | Any layout that lets the agent read `SKILL.md` on demand |
| Cursor | project `.cursor/rules/` or `AGENTS.md` | Reference the SKILL.md path in the rule text |

## Install

```sh
# 1. get the tool
git clone https://github.com/kolijijani/secret-vault.git
cd secret-vault

# 2. put the skill where the agent looks (rewrites the script path for you)
./install.sh ~/.claude/skills
```

`./install.sh` with no argument auto-detects the first existing directory from
`~/.hermes/skills`, `~/.claude/skills`, `~/.agents/skills`, `~/.config/agents/skills`.
Use `--dry-run` to preview.

Without the installer, copy `SKILL.md` and replace every `scripts/secret_form.py` with the absolute
path to your checkout. If you installed the CLI instead, replace it with `secret-vault`.

## Why the path matters

`SKILL.md` ships with `scripts/secret_form.py`, a repository-relative path. Copy only the markdown
and the agent will call a script that does not exist — the failure mode is a confused agent asking
you to paste a key into chat, which is exactly what this project prevents.

## Verify the handoff works

```sh
python3 scripts/secret_form.py --version
```

Then ask the agent for a form and confirm the page shows `// secret_vault`, `LIVE / SINGLE USE` and
a countdown. If the agent shows you a secret value in chat, stop and re-read the skill's "Rule
(never break)" section.
