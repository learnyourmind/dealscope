# AGENTS.md

Instructions for AI coding agents working in this repository (any tool).

The authoritative engineering guide is [`CLAUDE.md`](./CLAUDE.md) — read it first. Then:

1. [`intent.md`](./intent.md) — product purpose and principles.
2. [`spec.md`](./spec.md) — requirements and design (IDs: `FR-`, `OPS-`, `BD-`).
3. [`plan.md`](./plan.md) — ordered tasks; pick one whose dependencies are done.
4. [`docs/ai-sdlc.md`](./docs/ai-sdlc.md) — the task loop, human gates, and guardrails.

Essentials:

- Test first; run `make check` before claiming anything works. Report failures and unrun checks honestly.
- Never invent product behavior. If the spec is silent, record an open question and stop.
- No live network in tests; no secrets, real addresses, or upstream payloads in the repo.
- Never present an estimate as a retrieved fact, or fill missing data with a plausible default.
- Do not push, merge, change hosting, or touch production settings without explicit human approval.
