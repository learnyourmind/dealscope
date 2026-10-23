## What and why

<!-- One or two sentences. Link the plan.md task ID(s) and spec requirement ID(s). -->

Task: <!-- e.g. 1.3 -->  
Spec: <!-- e.g. FR-06, FR-07 -->

## Verification

- [ ] `make check` passes locally (lint, format, tests, coverage gate)
- [ ] New/changed behavior has a test that failed before the change
- [ ] Tests use mocked providers — no live network
- [ ] Bug fixed? Its `BD-xx` regression test is named in the description

## Product and safety checklist (delete rows that do not apply)

- [ ] Output distinguishes retrieved facts, user assumptions, and model estimates (spec §5.2)
- [ ] Missing/unavailable data is shown as unavailable — no silent defaults
- [ ] No exception text, stack trace, or upstream payload reaches the client
- [ ] No secrets, addresses, or request bodies added to code, logs, or fixtures
- [ ] `spec.md` / `README.md` / `intent.md` / `CLAUDE.md` updated if behavior, formulas, or limits changed

## AI assistance

- [ ] AI-assisted: tool/model and what it produced <!-- e.g. Claude Code drafted calc module; I reviewed and ran tests -->
- [ ] I read and understand every changed line, not only the summary

## Rollout / rollback

<!-- Usually "merge to main auto-deploys; rollback per docs/runbook.md". Note anything that differs. -->
