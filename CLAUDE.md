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

- `app.py` — Flask application, embedded HTML template, Redfin data access, regional assumptions, and the current financial analysis. Also serves `GET /healthz`.
- `README.md` — setup instructions, documented analysis features, and limitations.
- `requirements.txt` / `requirements-dev.txt` — runtime and development (pytest, ruff, pip-audit) dependencies.
- `run.sh` / `run.bat` — local startup scripts for macOS/Linux and Windows.
- `Procfile` — Gunicorn web process definition for Procfile-based platforms.
- `Dockerfile`, `render.yaml` — production image and Render blueprint (see [ADR-0003](./docs/adr/0003-docker-on-render-with-ci-gated-deploys.md)).
- `pyproject.toml`, `Makefile` — ruff/pytest/coverage configuration and the `make` entry points below.
- `tests/` — pytest suite (route smoke tests; independent check of the spec's golden calculation vectors in `tests/fixtures/golden_vectors.json`).
- `.github/` — CI (`ci.yml`), post-deploy smoke workflow, Dependabot, PR and task templates.
- `docs/` — `ai-sdlc.md`, `runbook.md` (deploy, rollback), `adr/` (architecture decisions).
- `scripts/smoke.sh` — post-deploy check (`/healthz` and `/` must return 200).
- `.env.example` — every configuration variable (no secrets today).

There is currently no separate frontend, database, or application configuration module (the spec's `dealscope/` package is planned, not present). Do not assume these exist.

## Implemented baseline and documentation gap

The current code is much smaller than the feature list in `README.md`:

- `app.py` defines a Flask app with `/` and `POST /analyze`.
- The root route renders the `HTML` string in `app.py`; that string currently contains a placeholder rather than a working interface.
- `RedfinEngine` calls Redfin's unofficial public endpoints to search for a property and retrieve details and comparable sales.
- `PropertyAnalyzer.analyze` calculates a basic estimate using regional constant tables. Its current response includes property basics, monthly cash flow, cap rate, down payment, monthly principal and interest, estimated rent, and a basic BUY/CAUTION verdict.
- The current analysis does not return most of the richer data described in the README (for example market snapshots, price history, detailed projections, investor scores, or risks/opportunities). The fetched comparable sales are not currently included in the response.
- Some unavailable values use hard-coded fallback assumptions. Treat resulting numbers as estimates, not verified property facts.

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
- Treat Redfin endpoints as unofficial and potentially unavailable or changed. Use bounded network timeouts, check HTTP status, and handle expected upstream failures explicitly when modifying network access.
- Keep regional rates and rent assumptions identifiable as estimates. Avoid implying that state-level averages are property-specific or current quotes.
- Do not add API keys or credentials to the repository. If a future provider requires credentials, use environment configuration and document setup without recording secrets.
- The app enables Flask-CORS globally and binds to `0.0.0.0` when run directly. Consider the security and deployment implications before expanding exposure or accepting new kinds of input.
- `requirements.txt` is the dependency manifest. Keep local startup scripts consistent with it when changing dependencies.

## Useful commands

Run locally:

```bash
python -m pip install -r requirements.txt
python app.py
```

The development server uses `PORT` when set and otherwise listens on port `5000`. `bash run.sh` and `run.bat` are the platform startup scripts. Deployment uses the `web: gunicorn app:app` command in `Procfile`.

Development workflow (creates `.venv` on first run):

```bash
make install   # venv + runtime and dev dependencies
make check     # ruff lint + format check, pytest with coverage gate, py_compile — what CI runs
make audit     # pip-audit on requirements.txt
```

`make test` runs only pytest. The coverage gate in `pyproject.toml` is a ratchet: raise it when coverage rises, never lower it to get a change through. Tests must not touch the network.

Build and smoke-test the production image (needs Docker):

```bash
make docker
make smoke URL=https://your-service.onrender.com
```

## Definition of done

A change is ready when its intended behavior is implemented, failure behavior is explicit, relevant checks pass, and product documentation accurately describes what users can do and what assumptions or limitations remain.
