---
description: Detect drift between spec.md, plan.md, README.md, CLAUDE.md and the code
---

Compare the documents with the code and report drift. Read-only unless I ask for fixes.

1. List what `app.py` and `dealscope/` (if present) actually implement: routes, response fields, error codes, bounds, assumption values.
2. Compare against `spec.md` (§5.2 formulas and bounds, §5.3 API and error codes, §6.3 configuration), `README.md` (features claimed), `CLAUDE.md` (current-state section), and `plan.md` (statuses).
3. For each mismatch give: file and section, what the document says, what the code does, and which should change (code or document). Flag any `BD-xx` defect that appears fixed but has no regression test, and any plan task marked `done` whose **Done when** check does not exist.
4. Do not edit the spec to match buggy code; surface it as a decision.
