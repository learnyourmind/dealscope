# ADR-0004: Deploy on Vercel

- **Status:** Accepted (owner requested Vercel)
- **Date:** 2026-10-23
- **Supersedes:** hosting choice in [ADR-0003](./0003-docker-on-render-with-ci-gated-deploys.md)

## Context
The owner wants the app on Vercel. Vercel's Python runtime serves a Flask WSGI app exposed as a module-level `app`; `app.py` already provides one. The app is stateless (ADR-0002).

## Decision
- Deploy the Flask app to Vercel with `requirements.txt` for dependencies, `.python-version` (3.12) for the runtime, and `.vercelignore` to keep tests, docs, and tooling out of the bundle.
- Production configuration is set as Vercel environment variables (`APP_ENV=production`; the provider stays `disabled`).
- Keep the `Dockerfile`, built and smoke-tested by CI, so hosting can change without code changes.
- Releases come from `main`. Connecting the GitHub repository in the Vercel dashboard gives automatic deploys; require the CI checks via branch protection so only green commits reach `main`.

## Consequences
- Serverless: cold starts on idle; no background workers; the in-process rate limiter is per instance (add Vercel Firewall or an edge limiter before heavy public exposure).
- Function duration limits apply (the app budgets 15 s for upstream calls; check the plan's limit before enabling a slow provider).
- Rollback is "promote a previous deployment" in Vercel (see `docs/runbook.md`).
- Gunicorn is not used on Vercel; it remains for the Docker image and `Procfile`.

## Alternatives considered
Render with Docker (ADR-0003); Fly.io/Cloud Run (more setup than needed).
