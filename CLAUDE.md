# DealScope — Claude Code Project Guide

## Project at a glance

DealScope is a Python/Flask web app intended to help US residential real-estate investors evaluate a property. Its documented product direction includes property data, rental estimates, operating expenses, investment metrics, comparable sales, market context, and buy-box recommendations.

Keep this guide and [intent.md](./intent.md) in view when working on the project. `CLAUDE.md` describes the repository and engineering practices; `intent.md` describes the product goal and how to assess proposed features.

## Document hierarchy (read in this order)

1. [intent.md](./intent.md) — why: product purpose, principles, acceptance criteria.
2. [spec.md](./spec.md) — what and how: requirements (`FR-`, `OPS-`), known defects (`BD-`), formulas, API, design, decision log.
3. [plan.md](./plan.md) — in what order: phased tasks with status and a "Done when" check each.
4. [docs/ai-sdlc.md](./docs/ai-sdlc.md) — the task loop, human gates, and guardrails for AI agents. Slash commands: `/next-task`, `/verify`, `/spec-sync`; reviewer subagent: `spec-reviewer` (all in `.claude/`).

If the spec is silent or contradictory, do not invent behavior: record an open question and stop. Product defaults in spec §11.1 are *proposed* until the decision log says approved.

## Repository map

- `app.py` — Flask app factory, routes, error handling, logging. Business logic lives in `dealscope/`; HTML in `templates/`, assets in `static/`.
- `README.md` — setup instructions, documented analysis features, and limitations.
- `requirements.txt` / `requirements-dev.txt` — runtime and development (pytest, ruff, pip-audit) dependencies.
- `run.sh` / `run.bat` — local startup scripts for macOS/Linux and Windows.
- `Procfile` — Gunicorn web process definition for Procfile-based platforms.
- `Dockerfile` — portable production image (built and smoke-tested in CI). `.python-version`, `.vercelignore` — Vercel deployment (see [ADR-0004](./docs/adr/0004-deploy-on-vercel.md); Docker kept for portability, see ADR-0003).
- `ruff.toml`, `pytest.ini`, `.coveragerc`, `Makefile` — lint/test/coverage configuration and the `make` entry points below. Do **not** add a `pyproject.toml`: Vercel would install from it and skip `requirements.txt` (ADR-0004).
- `tests/` — pytest suite (validation, analysis against the golden financial and price vectors in `tests/fixtures/golden_vectors.json`, Census adapter with synthetic payloads, bundled-data sanity, API and UI routes). No live network. `--confcutdir=tests` in `pytest.ini` keeps pytest from scanning the repo root.
- `.github/` — CI (`ci.yml`), post-deploy smoke workflow, Dependabot, PR and task templates.
- `docs/` — `ai-sdlc.md`, `runbook.md` (deploy, rollback), `adr/` (architecture decisions).
- `scripts/smoke.sh` — post-deploy check (`/healthz` and `/` must return 200).
- `.env.example` — every configuration variable (no secrets today).

There is no database, cache, or separate frontend build. Do not assume these exist.

## Implemented baseline and documentation gap

Shipped (see `plan.md` for status; direction per ADR-0005):

- `app.py` — `create_app()` factory (module-level `app` for Gunicorn/Vercel): `GET/POST /` (server-rendered page), `POST /analyze` (JSON API), `GET /healthz`; error envelope, request IDs, structured logging without addresses, optional CORS, per-process rate limit.
- `dealscope/` — `validation.py` (bounds; address is the only required input), `provider.py` (Census Geocoder + bundled ZIP market data + shared bounded HTTP helper), `homes.py` (RentCast home record and rent estimate, enabled only with `RENTCAST_API_KEY`), `analysis.py` (financials, closed-form price solver, provenance), `assumptions.py` (state tax/insurance tables, default rates), `service.py`, `errors.py`, `config.py`, `ratelimit.py`, `forms.py`.
- `data/zip_market.json` — Zillow Research ZIP rent/home-value snapshot, rebuilt by `scripts/update_market_data.py` (never hand-edit).
- `templates/index.html`, `static/` — dark/light, no-JS-required UI; no third-party requests.
- Every value is classified `retrieved | user | estimate | unavailable`. No BUY/PASS verdicts: prices are calculations from the user's criteria.

Not shipped: condition, list price, assessor records, comps, price history, projections, scores, county-level tax. The home is always analyzed as one whole unit, never room by room. With `RENTCAST_API_KEY` the home's configuration and own rent come from RentCast (verified live on 2026-10-23); without it the unit is a typical home in the ZIP and the configuration shows "not identified". The key is a secret: never log, print, commit, or put it in a fixture. Tax and insurance use unverified state-average constants.

When changing functionality, distinguish clearly between what is implemented and what is aspirational. Update the README whenever the shipped behavior or setup instructions change.

## Engineering workflow

For each feature or fix:

1. Read the relevant implementation and the corresponding product intent before editing.
2. Identify the user-visible behavior, inputs, output shape, and failure cases.
3. Make the smallest complete change that fits the existing Flask/Python structure. Keep route handling, calculations, and presentation coherent; avoid adding infrastructure without a concrete need.
4. Validate inputs and external-data assumptions. Surface actionable errors; do not silently convert request failures or missing data into authoritative-looking results.
5. Add or update focused tests for calculations, routes, and response shapes when a test framework is introduced or available.
6. Run the narrowest applicable test, lint, or syntax check. Report anything that could not be verified.
7. Update `README.md` and/or `intent.md` if user-facing behavior, limitations, or product direction changed.

## Technical conventions and constraints

- Use Python and the existing Flask application unless the task calls for a deliberate architectural change.
- Keep analysis outputs JSON-serializable and preserve the existing `success`/`error` response convention unless changing it intentionally and consistently.
- Only use free public data sources whose terms permit the use; never scrape listing sites or use unofficial endpoints without a terms review. Use bounded network timeouts, check HTTP status, and handle expected upstream failures explicitly when modifying network access.
- Keep regional rates and rent assumptions identifiable as estimates. Avoid implying that ZIP- or state-level figures are property-specific or current quotes.
- Do not add API keys or credentials to the repository. If a future provider requires credentials, use environment configuration and document setup without recording secrets.
- CORS is off unless `CORS_ORIGINS` lists origins (and then applies to `POST /analyze` only). The dev server binds to `127.0.0.1` unless `HOST` is set. Consider the security and deployment implications before expanding exposure or accepting new kinds of input.
- `requirements.txt` is the dependency manifest. Keep local startup scripts consistent with it when changing dependencies.

## Useful commands

Run locally:

```bash
python -m pip install -r requirements.txt
python app.py
```

The development server uses `PORT` when set and otherwise listens on port `5000`. `bash run.sh` and `run.bat` are the platform startup scripts. Procfile platforms use `web: gunicorn app:app`; Vercel runs the module-level `app` directly.

Development workflow (creates `.venv` on first run):

```bash
make install   # venv + runtime and dev dependencies
make check     # ruff lint + format check, pytest with coverage gate, py_compile — what CI runs
make audit     # pip-audit on requirements.txt
```

`make test` runs only pytest. The coverage gate in `pytest.ini` is a ratchet: raise it when coverage rises, never lower it to get a change through. Tests must not touch the network.

Build and smoke-test the production image (needs Docker):

```bash
make docker
make smoke URL=https://your-deployment.vercel.app
```

## Definition of done

A change is ready when its intended behavior is implemented, failure behavior is explicit, relevant checks pass, and product documentation accurately describes what users can do and what assumptions or limitations remain.
