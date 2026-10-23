# ADR-0002: Keep Flask, server-rendered UI, no database or AI service for the initial release

- **Status:** Accepted (follows spec §6 and §3.2)
- **Date:** 2026-10-23

## Context
The product is a stateless first-pass calculator. `CLAUDE.md` and `spec.md` ask for the smallest change that fits the existing structure and for no infrastructure without a concrete need. Addresses are sensitive, so not storing them is also a privacy benefit.

## Decision
- Keep Flask, served by Gunicorn.
- Extract logic from `app.py` into a small `dealscope/` package with a provider boundary (spec §6.1); keep `app.py` as the entry point (`app:app`) so `Procfile`, Docker, and Render are unaffected.
- Render HTML with Jinja templates and plain CSS/JS; no frontend framework or build step.
- No database, cache, or queue; no LLM/AI service.

## Consequences
- Horizontal scaling is trivial (stateless). Cold starts are fast.
- No saved portfolios or history — consistent with non-goals. Adding persistence later requires a new ADR, retention policy, and privacy review.
- Rate limiting is per-process unless done at the edge; acceptable at this scale (spec §5.5).

## Alternatives considered
FastAPI + SPA (more moving parts, no stated need); SQLite for caching provider results (undefined provider terms on caching, spec §7).
