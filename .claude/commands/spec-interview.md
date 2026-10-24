---
description: Interview the owner about a feature, then write a self-contained spec delta (Anthropic's interview pattern)
argument-hint: "<brief description of the feature>"
---

I want to build: $ARGUMENTS

Interview me with the AskUserQuestion tool. Skip obvious questions; dig into the hard parts: required inputs (the address stays the only required input), data sources and their terms, failure and missing-data behavior, wording that could read as advice, privacy, cost or quota, and how we will verify it end to end.

When we have covered everything, write the delta as: new or changed `FR-` requirements, bounds and error codes, golden test vectors, out-of-scope items, and an end-to-end verification step, in the style of `spec.md`. Update `plan.md` with tasks that each name their "Done when" check. Do not implement. Recommend starting a fresh session to execute the plan.
