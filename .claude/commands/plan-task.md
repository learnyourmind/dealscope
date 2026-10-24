---
description: Explore and plan a change WITHOUT editing anything (Anthropic's explore → plan step)
argument-hint: "<what you want, or a plan.md task id>"
---

Plan only. Do not edit files, run formatters, or commit. Work for: $ARGUMENTS

1. **Explore.** Read the relevant `intent.md` principles, `spec.md` requirements (cite IDs), `plan.md` task, and the code and tests you would touch. Use a subagent for wide searches so this context stays small.
2. **Check the premises.** List anything the spec leaves open or contradicts, and any external fact you would be assuming. If a data source, license, or secret is involved, say what is verified and what is not.
3. **Plan.** Give: files to change and why; the failing test(s) to write first (name them); the verification you will run (`make check`, `make scan`, a smoke command); risks and rollback; what is explicitly out of scope.
4. **Stop** and wait for approval. If the change can be described in one sentence, say so and propose skipping the plan.
