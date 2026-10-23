---
description: Run all local checks and an independent spec review of the current diff
---

1. Run `make check`. Show the actual result. If a tool is missing, say which check was not run — do not substitute a weaker one silently.
2. Run `git diff main...HEAD` (and uncommitted changes) to see what is under review.
3. Invoke the `spec-reviewer` subagent with that diff and the task ID(s) it implements.
4. Report: checks passed/failed, reviewer findings ordered by severity, and anything left unverified. Do not fix issues unless asked; if asked, fix and re-run.
