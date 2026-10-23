# DealScope Runbook

Operational procedures for the deployed service (Vercel; Docker image kept for portability). Spec references: OPS-01 … OPS-07.

## Environments

| Environment | Source | Deploy trigger | URL |
|---|---|---|---|
| Local | working tree | `make run` (dev server, `127.0.0.1:5000`) | `http://localhost:5000` |
| Production | `main` | Vercel Git integration once connected; the first release was a CLI deploy | repository variable `PROD_URL` |

Configuration is by environment variable only (`spec.md` §6.3, `.env.example`). Change it in Vercel → Project → Settings → Environment Variables, then redeploy (variables apply to new deployments only).

Production variables: `APP_ENV=production`. `GEOCODER` defaults to `census`; set `GEOCODER=disabled` to switch address lookup off. Refresh market data monthly: `python scripts/update_market_data.py`, review the as-of dates, and open a PR.

## First-time setup (human, once)

1. Open the pull request and confirm the `test` and `docker` checks pass.
2. GitHub → Settings → Branches: protect `main` — require a pull request, require the `test` and `docker` status checks, block force-pushes.
3. Vercel dashboard → the `dealscope` project → Settings → Git → connect the GitHub repository, production branch `main`. (Until then, deploy manually — see Release.)
4. GitHub → Settings → Secrets and variables → Actions → Variables → add `PROD_URL` (the production domain, e.g. `https://dealscope-xxxx.vercel.app`). Run **Actions → Deployed smoke check → Run workflow**.

## Release

With Git integration: merge the approved PR to `main`; Vercel builds and promotes automatically. Manual (CLI, needs Node and `vercel login`):

```bash
export PATH="$HOME/.local/node/bin:$PATH"   # if Node is installed there
vercel deploy --prod --yes
```

Then run the smoke check (Actions → **Deployed smoke check**, or):

```bash
make smoke URL=https://<production-domain>
```

If anything fails, roll back.

## Rollback

Target: restore the previous version in under 10 minutes without editing code.

1. Vercel → Project → **Deployments** → open the last good production deployment → **⋯ → Promote to Production** (or `vercel rollback`).
2. Run the smoke check.
3. Make the repository match: `git revert <bad-sha>` on a branch, open a PR, merge. Otherwise the next push redeploys the bad code.
4. Record what happened in a short post-incident note: trigger, detection, fix, and the test or guardrail added.

> Rehearsal record (plan D9): _not yet performed_. Fill in date, duration, and any surprises.

## Troubleshooting

| Symptom | Likely cause | Action |
|---|---|---|
| Build fails | Dependency or Python version problem | Vercel → Deployments → Build logs; reproduce with `make check` using Python 3.12 |
| Function error 500 on every request | Import error at start-up | Vercel → Logs; the `request_id` in the error body maps to a log line |
| Slow first request | Serverless cold start | Retry; `smoke.sh` already retries 6× |
| Many `PROVIDER_*` errors | Census Geocoder slow, throttling, or down | Retry later; do not loop. Open an issue with the request id; `GEOCODER=disabled` turns lookup off |
| Unexpected 429 | Per-instance rate limit (`RATE_LIMIT`) | Check for a client loop; raise only deliberately |
| 401 from the URL | Vercel Deployment Protection on preview URLs | Use the production domain, or `vercel curl` / a bypass token for previews |

## Logs and data handling

Logs are one-line JSON on stdout (Vercel captures them): request id, route, status, latency, error code — **not** addresses, request bodies, query strings, or upstream payloads (spec OPS-07). Do not add such fields while debugging; use a fixture. The service stores no user data.

## Secrets

`RENTCAST_API_KEY` is the only secret. Store it as a Vercel environment variable marked **Sensitive** (Project → Settings → Environment Variables), never in the repo, logs, screenshots, or chat. Rotate it in the RentCast dashboard if it may have leaked, then update Vercel and redeploy.

**Quota and billing:** the free RentCast plan allows 50 requests a month and charges $0.20 per request beyond that. Each analysis uses one request, and the app's rate limit is per instance, so cap or disable overage billing in the RentCast account and watch its usage page. When the quota is gone the app keeps working and shows the ZIP-typical home with the reason.

### If a secret was committed or pushed

Treat it as compromised the moment it reaches a remote, even on a branch, even if deleted later: this repository is public and GitHub keeps commits reachable by hash.

1. **Rotate first.** Regenerate the key in the provider's dashboard (RentCast → API) so the leaked value stops working.
2. Put the new key only in the host secret store: `vercel env add RENTCAST_API_KEY production` (paste it at the prompt; choose Sensitive in the dashboard), then redeploy (`vercel redeploy <production-url>`).
3. Remove the value from the working tree and branches: restore the template (`git checkout origin/main -- .env.example`), delete the leaking branch (`git push origin --delete <branch>`). Rewriting history is optional and does not make the old key safe; rotation does.
4. `tests/test_repo_hygiene.py` fails CI if `.env.example` has a value for any KEY/SECRET/TOKEN/PASSWORD variable. Real keys never go in tracked files; use the host store or a git-ignored `.env`.

To switch the lookup off without changing code, delete the variable and redeploy; the app falls back to the ZIP-typical home.
