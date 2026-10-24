#!/usr/bin/env bash
# PostToolUse (Edit|Write): keep Python formatted and lint-clean after every edit.
INPUT=$(cat)
FILE=$(printf '%s' "$INPUT" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("tool_input",{}).get("file_path",""))' 2>/dev/null)
case "$FILE" in
  *.py) ;;
  *) exit 0 ;;
esac
RUFF="${CLAUDE_PROJECT_DIR:-.}/.venv/bin/ruff"
[ -x "$RUFF" ] || RUFF="$(command -v ruff || true)"
[ -n "$RUFF" ] || exit 0
"$RUFF" check --fix --quiet "$FILE" >/dev/null 2>&1
"$RUFF" format --quiet "$FILE" >/dev/null 2>&1
exit 0
