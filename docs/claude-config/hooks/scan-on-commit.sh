#!/usr/bin/env bash
# PreToolUse (Bash): run the secret scan before any `git commit` Claude runs.
INPUT=$(cat)
CMD=$(printf '%s' "$INPUT" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("tool_input",{}).get("command",""))' 2>/dev/null)
case "$CMD" in
  *"git commit"*) ;;
  *) exit 0 ;;
esac
cd "${CLAUDE_PROJECT_DIR:-.}" || exit 0
if ! OUT=$(python3 scripts/scan_secrets.py --staged 2>&1); then
  echo "Blocked: the staged changes look like they contain a secret (values are not shown)." >&2
  echo "$OUT" | head -20 >&2
  exit 2
fi
exit 0
