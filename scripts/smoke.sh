#!/usr/bin/env bash
# Post-deploy smoke check (spec OPS-04). Usage: scripts/smoke.sh https://host
set -euo pipefail

base="${1:?usage: smoke.sh <base-url>}"
base="${base%/}"

check() {
  local path="$1" code
  code=$(curl -sS -o /dev/null -w '%{http_code}' --max-time 30 --retry 6 --retry-delay 5 \
    --retry-all-errors "$base$path")
  if [ "$code" != "200" ]; then
    echo "FAIL $path -> HTTP $code" >&2
    exit 1
  fi
  echo "ok   $path -> 200"
}

check /healthz
check /
