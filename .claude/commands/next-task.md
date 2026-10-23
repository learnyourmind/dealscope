---
description: Run the DealScope task loop for the next (or a named) plan.md task
argument-hint: "[task id, e.g. 1.3] (optional)"
---

Follow `docs/ai-sdlc.md` §2 for this task: $ARGUMENTS

1. Open `plan.md`. If an ID was given use it; otherwise take the first `todo` task whose **Depends** are all `done`. If its **Who** is `H`, or it is `blocked`, stop and tell me what human action is needed.
2. Read the spec requirements the task cites, `intent.md` principles that apply, and the code it will touch. Restate the **Done when** check in one sentence.
3. If the spec is silent or contradictory, list the open questions and stop — do not guess product behavior, bounds, or wording.
4. Create a branch `task/<id>-<slug>`. Write the failing test first and show it failing for the right reason.
5. Implement the smallest change that fits the existing structure. No unrelated edits, no new dependency without a stated reason, no live network in tests.
6. Run `make check`. Report real results; say plainly if anything could not be run.
7. Invoke the `spec-reviewer` subagent on the diff and address real findings.
8. Update the task's status in `plan.md`, and `spec.md` / `README.md` if behavior, formulas, or limits changed.
9. Commit with a message citing the task and requirement IDs. Do not push. Summarize what changed, what was verified, and what the human should review.
