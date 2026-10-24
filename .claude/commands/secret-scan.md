---
description: Scan tracked and staged files for committed secrets (values are never printed)
---

1. Run `python3 scripts/scan_secrets.py --all`, then `python3 scripts/scan_secrets.py --staged`.
2. Report findings as FILE:LINE and rule only. Never print, quote, or paste a matched value, and never read `.env` files to "check" them.
3. If something is found: tell the owner to **rotate the credential first** if it was ever pushed (the repository is public), remove it from the file, and set the real value in the host secret store (Vercel → Environment Variables → Sensitive). Follow `docs/runbook.md` → "If a secret was committed or pushed".
4. Remind the owner to run `make hooks` once per clone so the pre-commit hook blocks this automatically.
