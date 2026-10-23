# AI-native SDLC for DealScope

How humans and AI agents (Claude Code or any comparable tool) build, verify, and ship DealScope. The aim: let an agent do the repetitive loop quickly, while a human keeps every decision that is legal, financial, or product-defining.

## 1. Artifact chain — each level constrains the next

| Level | File | Owner | Changes when |
|---|---|---|---|
| Why | `intent.md` | Product owner (human) | Product purpose or principles change |
| What and how | `spec.md` | Human decides, AI drafts | A requirement, formula, bound, or decision changes |
| In what order | `plan.md` | AI drafts, human approves | A task completes, is split, or a dependency changes |
| Do it | GitHub issue / branch / PR (`.github/ISSUE_TEMPLATE/task.md`) | AI executes, human reviews | Per task |
| Prove it | `tests/`, CI, smoke check | Both | Every PR |
| Run it | `Dockerfile`, `render.yaml`, `docs/runbook.md` | Both | Deployment changes |
| Why we chose | `docs/adr/` | Whoever decides | An architectural choice is made or reversed |

Agent context files — `CLAUDE.md` (engineering guide, loaded automatically), `AGENTS.md` (pointer for other tools), `.claude/` (permissions, commands, reviewer subagent) — encode the rules so each session starts with the same constraints.

## 2. The task loop (what `/next-task` does)

1. **Select.** Take the first `todo` task in `plan.md` whose dependencies are `done`, or the one named by the human. Stop if its **Who** is `H`.
2. **Read.** Read the task's spec requirement IDs, the relevant code, and `intent.md` principles. Restate the acceptance check in one sentence.
3. **Clarify or stop.** If the spec is silent or contradicts itself, write the question under the task's **Open questions** (PR description or issue) and stop. Do not invent product behavior, thresholds, or bounds.
4. **Test first.** Write the failing test named in **Done when**; run it and see it fail for the right reason.
5. **Implement the smallest change** that fits the existing Flask/Python structure. No unrelated refactors, no new dependencies without a stated need.
6. **Verify.** `make check`. Report the real output, including anything that could not be run (e.g. Docker not available).
7. **Self-review.** Run the `spec-reviewer` subagent on the diff (`/verify` does steps 6–7). Fix real findings; list the rest in the PR.
8. **Sync docs.** Update `plan.md` status, `spec.md`/`README.md` if behavior or limits changed.
9. **Open a PR** with the template filled in. The human reviews the diff, not just the summary.

## 3. Human gates — an agent never passes these alone

| Gate | Why |
|---|---|
| Provider terms and data-use rights (plan P0-1) | Legal; cannot be coded around (spec §7) |
| Product defaults, bounds, recommendation wording (plan P0-2, task 1.10) | Financial-advice risk (spec §7) |
| Brand and visual identity (P0-3) | No approved brand exists; agents must not invent one |
| Merging to `main` | Branch protection requires review plus green CI |
| Production configuration and secrets | Agents have no access to host dashboards or secret stores |
| Enabling real-provider traffic (`PROPERTY_PROVIDER`) | Depends on P0-1 |
| Rollback or hotfix to production | Human decides; runbook gives the procedure |

## 4. Guardrails for agents

- **Scope:** change only what the task names. Anything else noticed goes in the PR description or a new `plan.md` row.
- **Truthfulness over green:** never weaken, skip, or delete a test, ratchet, or check to get past it. Never report "done" without running the check.
- **No live network in tests.** Provider behavior is tested with recorded or synthetic fixtures. Do not probe Redfin, bypass rate limits, or work around bot protection (spec §7).
- **No secrets or personal data** in code, tests, fixtures, logs, or commits. Use fictional addresses (e.g. `100 Example St`) in fixtures.
- **Estimates are not facts.** Output code must preserve the `retrieved | user | estimate | unavailable` classification; never replace missing data with a plausible default (intent principle 6).
- **Dependencies:** add or upgrade only with a reason; CI runs `pip-audit`.
- **Destructive or outward actions** (force-push, deleting branches, changing hosting, posting externally) need explicit human approval each time.
- **Permissions** are pinned in `.claude/settings.json`: read/edit/test tooling allowed; pushing, secret files, and destructive shell commands denied.

## 5. Quality gates

| Stage | Gate | Where |
|---|---|---|
| Local | `make check` (ruff lint + format, tests, coverage ratchet, `py_compile`) | Developer / agent |
| Pull request | CI: lint, format, tests + coverage, `pip-audit`, Docker build + container smoke | `.github/workflows/ci.yml` |
| Review | Human review; `spec-reviewer` agent output attached | PR |
| Merge | Branch protection: PR + required checks `test`, `docker` | GitHub settings (plan D7) |
| Deploy | Render deploys only after checks pass; health check `/healthz` gates traffic | `render.yaml` |
| Post-deploy | `scripts/smoke.sh` via the `Deployed smoke check` workflow | `.github/workflows/smoke.yml` |
| Ongoing | Scheduled smoke; Dependabot PRs go through the same gates | Workflows, `dependabot.yml` |

## 6. Working in parallel

Tasks with disjoint files and satisfied dependencies (e.g. plan 1.1–1.4) can run in separate branches or git worktrees, each ending in its own PR. Never let two agents edit the same file concurrently. The task that wires things together (1.8) waits for the others.

## 7. Using AI inside the product

None today: spec §3.2 excludes LLM-generated recommendations and sending property or user data to an AI provider. If that changes, require first: an ADR, a data-handling and privacy review, an evaluation set with pass criteria, output labeling as model-generated, and the same provenance rules as every other estimate.

## 8. Keeping the process honest

- Review this document and the `plan.md` risk table at the end of each phase.
- When an agent makes a mistake that the process should have caught, add a test, a guardrail line here, or a `CLAUDE.md` rule — in the same PR as the fix.
- Record notable decisions as ADRs (`docs/adr/`) and spec decision-log entries (`spec.md` §12).
