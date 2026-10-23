# ADR-0001: Record architecture decisions

- **Status:** Accepted
- **Date:** 2026-10-23

## Context
Humans and AI agents both change this repository. Rationale that lives only in a chat or in someone's head is lost, and agents cannot distinguish a deliberate constraint from an accident.

## Decision
Record each significant, hard-to-reverse choice as a short ADR in `docs/adr/NNNN-title.md` with Status, Context, Decision, Consequences, and Alternatives. Product-level decisions (bounds, defaults, provider approval) go in the `spec.md` §12 decision log and may link to an ADR.

## Consequences
Small overhead per decision; agents and reviewers can find the reason before reopening a question. Superseded ADRs stay in place with status `Superseded by ADR-NNNN`.

## Alternatives considered
Wiki or issue comments (not versioned with the code); no records (the status quo).
