# DealScope Runbook

Operational procedures for the deployed service (Render, Docker, Gunicorn). Spec references: OPS-02 … OPS-07.

## Environments

| Environment | Source | Deploy trigger | URL |
|---|---|---|---|
| Local | working tree | `make run` (dev server) | `http://localhost:5000` |
| Production (initially non-announced) | `main` | Render auto-deploy once GitHub checks pass (`autoDeployTrigger: checksPass`) | set as repo variable `PROD_URL` |

Configuration is by environment variable only (`spec.md` §6.3, `.env.example`). Change it in the Render dashboard → service → Environment; a change restarts the service.

## First-time setup (human, once)

1. Push the repository; open a pull request and confirm the `test` and `docker` checks pass.
2. GitHub → Settings → Branches: protect `main` — require a pull request, require the `test` and `docker` status checks, block force-pushes.
3. Render → New → Blueprint → select the repository. Render reads `render.yaml`, builds the `Dockerfile`, and gates traffic on `/healthz`.
4. After the first deploy: GitHub → Settings → Secrets and variables → Actions → Variables → add `PROD_URL` (e.g. `https://dealscope.onrender.com`). Run **Actions → Deployed smoke check → Run workflow**.
5. Keep `PROPERTY_PROVIDER=disabled` until the provider-terms decision (plan P0-1) is recorded in `spec.md` §12.

## Release

1. Merge the approved pull request to `main` (CI is already green).
2. Render builds and deploys automatically. Watch Render → Events until "Live".
3. Run the smoke check: Actions → **Deployed smoke check**, or

```bash
make smoke URL=https://<your-service>.onrender.com
```

4. Open the site and run the primary journey once (when the UI exists). If anything fails, roll back.

## Rollback

Target: restore the previous version in under 10 minutes without editing code.

1. Render → service → **Events** (or **Deploys**) → find the last good deploy → **Rollback** / **Redeploy**.
2. Run the smoke check (above).
3. Make the repository match: `git revert <bad-sha>` on a branch, open a PR, merge. (Otherwise the next push redeploys the bad code.)
4. Record what happened in a short post-incident note: trigger, detection, fix, and the test or guardrail added.

> Rehearsal record (plan D9): _not yet performed_. Fill in date, duration, and any surprises after the first rehearsal.

## Troubleshooting

| Symptom | Likely cause | Action |
|---|---|---|
| Deploy fails health check | App crashed on boot or `/healthz` changed | Render → Logs; run `docker build` + `docker run -p 8000:8000` locally to reproduce |
| Smoke check times out on the first call | Free tier cold start | Re-run; `smoke.sh` already retries 6× |
| Many `PROVIDER_*` errors | Redfin unavailable, throttling, or changed payload | Do not retry in a loop. Set `PROPERTY_PROVIDER=disabled` to force manual entry (once FR-22 exists); open an issue with the request id |
| 5xx with `INTERNAL_ERROR` | Bug | Find the `request_id` in logs (the client receives it), reproduce with a fixture, fix with a regression test |
| Unexpected 429 | App rate limit (`RATE_LIMIT`) | Check for a client loop; raise only deliberately |

## Logs and data handling

Logs go to stdout (Render captures them). They contain request id, route, status, latency, and error code — **not** addresses, request bodies, or upstream payloads (spec OPS-07). Do not add such fields while debugging; use a fixture instead. The service stores no user data (spec §6, "Data persistence").

## Secrets

None today. If a licensed provider is added: store its key as a Render environment secret (never in the repo, `render.yaml`, logs, or screenshots), rotate it on suspected exposure, and add it to `.env.example` as an empty placeholder.
