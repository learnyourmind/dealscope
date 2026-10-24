#!/usr/bin/env bash
# OPTIONAL Stop hook: do not let a turn end while `make check` fails (deterministic gate).
# Register under "Stop" in settings (see README). Claude Code caps consecutive blocks.
cd "${CLAUDE_PROJECT_DIR:-.}" || exit 0
if ! OUT=$(make check 2>&1); then
  echo "make check is failing; fix it before finishing:" >&2
  echo "$OUT" | tail -25 >&2
  exit 2
fi
exit 0
