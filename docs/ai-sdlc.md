# AI-assisted SDLC for DealScope

How people and AI agents (Claude Code, or any comparable tool) build, verify, and ship DealScope. The goal: let an agent run the repetitive loop quickly, while a person keeps every decision that is legal, financial, secret-bearing, or product-defining.

> **Provenance.** Anthropic does not publish a single "AI SDLC" specification. This setup follows the practices in Anthropic's Claude Code documentation (best practices, hooks, skills, subagents, permissions, GitHub Actions), read on 2026-10-24 from <https://code.claude.com/docs/en/>. Section 7 maps each practice to the file that implements it, so gaps are visible.

## 1. Artifact chain — each level constrains the next

| Level | File | Owner | Changes when |
|---|---|---|---|
| Why | `intent.md` | Product owner (human) | Purpose or principles change |
| What and how | `spec.md` | Human decides, AI drafts | A requirement, formula, bound, or decision changes |
| In what order | `plan.md` | AI drafts, human approves | A task completes, splits, or a dependency changes |
| Do it | branch, PR (`.github/ISSUE_TEMPLATE/task.md`, PR template) | AI executes, human reviews | Per task |
| Prove it | `tests/`, CI, smoke check | Both | Every PR |
| Run it | `.python-version`, `.vercelignore`, `Dockerfile`, `docs/runbook.md` | Both | Deployment changes |
| Why we chose | `docs/adr/` | Whoever decides | An architectural choice is made or reversed |

Agent context: `CLAUDE.md` (kept short on purpose; loaded every session), `AGENTS.md` (pointer for other tools), `.claude/` (commands, subagents; permissions in `settings.json`).

## 2. The task loop (explore → plan → implement → verify → review → commit)

1. **Explore.** Read the cited `spec.md` requirements, `intent.md` principles, and the code. `/plan-task` does this without editing. Use a subagent for wide searches so the main context stays small.
2. **Plan** when the change touches several files, an unfamiliar area, or an external source. If you could describe the diff in one sentence, skip the plan. List the failing test first and the checks you will run.
3. **Clarify or stop.** If the spec is silent or contradicts itself, write the question down and stop. For a larger feature run `/spec-interview` to turn an interview into a spec delta and plan tasks.
4. **Test first.** Write the failing test named in the task's "Done when"; see it fail for the right reason.
5. **Implement the smallest change** that fits the existing structure. No unrelated refactors; no new dependency without a stated reason.
6. **Verify with evidence.** `make check` (lint, secret scan, tests, coverage ratchet) and any task-specific check (`make smoke`, a browser check). Report real output; say what could not run.
7. **Independent review in a fresh context.** `/verify` runs `make check` and the `spec-reviewer` subagent; use `security-reviewer` for network, config, logging, or dependency changes; `/code-review` for a bug-focused pass. Tell reviewers to flag only gaps that affect correctness or requirements.
8. **Sync docs**, then commit and open a PR (template filled in). A person reviews the diff, not only the summary.

Between unrelated tasks use `/clear`. After two failed corrections on the same issue, start fresh with a better prompt. Run parallel work in separate git worktrees (one branch and PR each); never let two sessions edit the same files.

## 3. Human gates — an agent never passes these alone

| Gate | Why |
|---|---|
| Data-source terms and licenses (RentCast, Zillow Research, Census) | Legal; cannot be coded around (spec §7) |
| Product defaults, bounds, and price wording | Advice risk (spec §7) |
| Brand and visual identity | No approved brand exists; agents must not invent one |
| Creating, rotating, or viewing secrets; billing caps | Only the owner holds the accounts; agents never see key values |
| Merging to `main`; enabling Actions permissions or the Claude workflows | Branch protection plus the owner's say |
| Production configuration, rollbacks, deleting remote branches | Outward-facing and hard to reverse |
| Installing hooks and changing `.claude/settings.json` | They execute commands; the agent cannot write them (`docs/claude-config/`) |

## 4. Guardrails for agents

- **Scope:** change only what the task names; anything else goes in the PR text or a new `plan.md` row.
- **Truthfulness over green:** never weaken, skip, or delete a test, ratchet, or check to get past it; never report "done" without running the check.
- **No live network in tests.** Use fixtures; do not probe providers or bypass limits or bot protection. Live checks against paid APIs are deliberate, counted, and few.
- **Secrets:** never read, print, log, commit, or paste a key. `.env.example` is names-only (a CI test enforces it). Real values live only in the host secret store. If one is ever committed, rotate first (`docs/runbook.md`).
- **Estimates are not facts.** Preserve `retrieved | user | estimate | unavailable`; never fill missing data with a plausible default.
- **One home, one unit.** Never price or rent by room.
- **Destructive or outward actions** (force-push, deleting branches, changing hosting, billing, or Actions settings) need explicit approval each time.
- **Permissions** are in `.claude/settings.json`: read/edit/test tooling allowed; force-push, hard reset, `rm -rf`, and reads of `.env*` denied. The sandbox restricts files and network further.

## 5. Quality gates

| Stage | Gate | Where |
|---|---|---|
| Edit time (optional, owner-installed) | Hooks: block edits to `.env*` and generated data, format Python, scan before `git commit` | `docs/claude-config/` |
| Commit | `.githooks/pre-commit` secret scan (`make hooks` once per clone) | `scripts/scan_secrets.py` |
| Local | `make check` = ruff lint + format, secret scan, tests with coverage ratchet, compile | Makefile |
| Pull request | CI: lint, format, secret scan, tests + coverage, `pip-audit`, Docker build + container smoke | `.github/workflows/ci.yml` |
| Review | Human; `spec-reviewer` / `security-reviewer` output; optional Claude review workflow | PR |
| Merge | Branch protection: PR + required checks | GitHub settings |
| Deploy | Vercel production from `main` | `docs/runbook.md` |
| Post-deploy | `scripts/smoke.sh`; axe on the UI; `/healthz` reports the commit | smoke workflow, release checklist |
| Ongoing | Scheduled smoke; Dependabot; monthly data refresh PR | workflows |

## 6. Using AI inside the product

None. The product makes no LLM calls and sends no user data to an AI provider (spec §3.2). If that changes: an ADR, a privacy and data-handling review, an evaluation set with pass criteria, output labeled as model-generated, and the same provenance rules as every other estimate.

## 7. Mapping to Anthropic's Claude Code guidance

| Anthropic practice (docs) | In this repo | Status |
|---|---|---|
| Give Claude a way to verify its work (tests, build, linter, screenshots) | `make check`, golden vectors, round-trip price tests, smoke script, axe checks | Active |
| Explore, plan, then code; skip the plan for one-line diffs | `/plan-task`; task loop §2 | Active |
| Let Claude interview you and write a spec | `/spec-interview` → `spec.md` / `plan.md` | Active |
| Concise CLAUDE.md; prune; skills for occasional workflows | Short `CLAUDE.md`; workflows in commands and the skill example | Active |
| Permissions allowlists and sandboxing | `.claude/settings.json` allow/deny; sandbox | Active |
| Custom subagents for isolated review | `spec-reviewer`, `security-reviewer` | Active |
| Adversarial review in a fresh context | `/verify`, subagents, `/code-review` | Active |
| Custom slash commands / skills | `.claude/commands/*` active; `release-check` skill example | Active / owner installs the skill |
| Hooks for must-always-happen actions | Four hook scripts + settings snippet | **Owner installs** (`docs/claude-config/`) |
| Parallel sessions with git worktrees; writer/reviewer split | Section 2; worktrees used for parallel branches | Practice |
| Non-interactive / CI use; Claude Code GitHub Action | `claude.yml`, `claude-review.yml` (inert until enabled) | **Owner enables** |
| Credential hygiene: secrets only in the host store | Scanner, pre-commit hook, hygiene tests, runbook procedure | Active |
| MCP servers for external tools | Not needed: `gh`, `vercel`, and `curl` CLIs cover it | Not used |
| Plugins | Not needed | Not used |

Re-check this table when Anthropic's guidance changes; unfilled rows are the backlog.
