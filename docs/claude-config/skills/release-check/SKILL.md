---
name: release-check
description: Pre-merge and post-deploy checklist for DealScope (checks, secret scan, spec drift, smoke, accessibility). Use when asked to verify a PR is ready to merge or that production is healthy.
disable-model-invocation: true
---

Run the DealScope release checklist for: $ARGUMENTS

1. `make check` and `make scan`; show the real output. Say plainly if a check could not run.
2. `git diff main...HEAD`: confirm every changed requirement has a test that failed before, that `spec.md`, `plan.md`, `README.md`, and `CLAUDE.md` still match the behavior, and that no secret, real address, or upstream body is in code, fixtures, logs, or docs.
3. Use the `spec-reviewer` and `security-reviewer` subagents on the diff; fix real findings, list the rest.
4. After merge and deploy: `make smoke URL=<production>`; confirm `/healthz` reports the merge commit; for a UI change, run axe on the home, results, and error pages in light and dark.
5. Report: what passed, what failed, what is unverified, and any owner-only follow-ups (billing caps, secrets, terms).
