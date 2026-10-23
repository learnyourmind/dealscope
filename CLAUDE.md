# DealScope — Claude Code Project Guide

## Project at a glance

DealScope is a Python/Flask web app intended to help US residential real-estate investors evaluate a property. Its documented product direction includes property data, rental estimates, operating expenses, investment metrics, comparable sales, market context, and buy-box recommendations.

Keep this guide and [intent.md](./intent.md) in view when working on the project. `CLAUDE.md` describes the repository and engineering practices; `intent.md` describes the product goal and how to assess proposed features.

## Repository map

- `app.py` — Flask application, embedded HTML template, Redfin data access, regional assumptions, and the current financial analysis.
- `README.md` — setup instructions, documented analysis features, and limitations.
- `requirements.txt` — Python runtime dependencies.
- `run.sh` / `run.bat` — local startup scripts for macOS/Linux and Windows.
- `Procfile` — Gunicorn web process definition for deployment platforms.

There is currently no separate frontend, test suite, database, or application configuration module. Do not assume these exist.

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

No test command is currently defined. For a basic syntax check, run:

```bash
python -m py_compile app.py
```

Add a repeatable test command when tests are added, and document it here and in the README.

## Definition of done

A change is ready when its intended behavior is implemented, failure behavior is explicit, relevant checks pass, and product documentation accurately describes what users can do and what assumptions or limitations remain.
