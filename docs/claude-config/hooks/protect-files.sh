#!/usr/bin/env bash
# PreToolUse (Edit|Write): block edits to files that must never be hand-edited by an agent.
# Exit code 2 blocks the call and sends the message to Claude as feedback.
INPUT=$(cat)
FILE=$(printf '%s' "$INPUT" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("tool_input",{}).get("file_path",""))' 2>/dev/null)
FILE="${FILE//\\//}"
base="${FILE##*/}"

block() { echo "Blocked: $1" >&2; exit 2; }

# Real environment files hold secrets. The names-only template (.env.example) is allowed.
case "$base" in
  .env.example) ;;
  .env|.env.*) block "$FILE is an environment file; put secrets in the host secret store, never in files" ;;
esac
case "$FILE" in
  */data/zip_market.json) block "data/zip_market.json is generated; run scripts/update_market_data.py" ;;
  */.git/*) block "do not edit git internals" ;;
esac
exit 0
