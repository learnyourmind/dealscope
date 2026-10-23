# ADR-0003: Deploy as a Docker image on Render, gated by CI

- **Status:** Proposed — the hosting choice is reversible and awaits owner confirmation
- **Date:** 2026-10-23

## Context
The README names Railway, Render, and PythonAnywhere. The repository has a `Procfile` (`web: gunicorn app:app`) but no container or pipeline. Requirements: HTTPS, automatic deploy only after tests pass, health-checked releases, quick rollback, low cost (spec OPS-01 … OPS-05).

## Decision
- Build with a `Dockerfile` (Python 3.12 slim, non-root, Gunicorn, `HEALTHCHECK`).
- Declare the service in `render.yaml` with `healthCheckPath: /healthz` and `autoDeployTrigger: checksPass`, so Render deploys a commit only after the GitHub CI checks succeed.
- Keep `Procfile` for Procfile-based hosts; the Docker `CMD` is the authoritative production command.
- Post-deploy verification is a GitHub Actions smoke workflow against `PROD_URL`.

## Consequences
- Portable: the same image runs on Fly.io, Cloud Run, or Railway with a small config swap.
- Render free tier sleeps when idle (cold-start latency); acceptable pre-launch, revisit before public launch.
- The Dockerfile has not been built in the authoring environment; the CI `docker` job is the first real build.
- `autoDeployTrigger` is a Render setting; verify it in the Render dashboard on first deploy.

## Alternatives considered
Procfile-only buildpack deploy (less control of runtime and no local parity); GitHub Actions pushing images to a registry (more setup than needed for one service).
