#!/bin/sh
# Install the confidential-input-form skill into a local AI agent's skill directory.
#
#   ./install.sh                      # auto-detect Hermes / Claude Code / generic agent dirs
#   ./install.sh ~/.claude/skills     # explicit skill root
#   ./install.sh ~/.claude/skills --dry-run
#
# The skill's script path is rewritten to this checkout, because SKILL.md ships
# with a relative path that only resolves inside the repository.
set -eu

here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
script="$here/scripts/secret_form.py"
name="confidential-input-form"
dry_run=0

dest=""
for arg in "$@"; do
  case "$arg" in
    --dry-run) dry_run=1 ;;
    -h|--help) sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) dest="$arg" ;;
  esac
done

if [ ! -f "$script" ]; then
  echo "error: $script not found — run this from a checkout of the repository" >&2
  exit 1
fi

if [ -z "$dest" ]; then
  for candidate in "$HOME/.hermes/skills" "$HOME/.claude/skills" "$HOME/.agents/skills" "$HOME/.config/agents/skills"; do
    if [ -d "$candidate" ]; then
      dest="$candidate"
      break
    fi
  done
fi

if [ -z "$dest" ]; then
  cat >&2 <<EOF
No agent skill directory found. Pass one explicitly, for example:

  ./install.sh ~/.claude/skills
  ./install.sh ~/.hermes/skills

Then tell your agent to read $name/SKILL.md when it needs a secret.
EOF
  exit 1
fi

target_dir="$dest/$name"
printf 'skill dir : %s\n' "$target_dir"
printf 'script    : %s\n' "$script"

if [ "$dry_run" -eq 1 ]; then
  echo "dry run: nothing written"
  exit 0
fi

mkdir -p "$target_dir"
# Rewrite the relative script path so the installed copy points at this checkout.
sed "s|scripts/secret_form.py|$script|g" "$here/SKILL.md" > "$target_dir/SKILL.md"
chmod 644 "$target_dir/SKILL.md"

cat <<EOF

Installed.

  SKILL.md : $target_dir/SKILL.md
  script   : $script

Quick check (prints a one-time URL, no secret involved):

  python3 "$script" --version
  python3 "$script" --spec "$here/examples/api-key.json" --expire-minutes 10

Never bind 0.0.0.0 — pass your localhost or private-network address.
EOF
