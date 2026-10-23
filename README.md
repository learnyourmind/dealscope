# DealScope — What can you pay for a rental?
### No API keys required · Python / Flask

## Quick Start

### Mac / Linux:
```bash
bash run.sh
```
Then open: **http://localhost:5000**

### Windows:
Double-click `run.bat`  
Then open: **http://localhost:5000**

### Manual:
```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python app.py
```

## Project Status

Type an address; get the price a rental can support.

- **Input:** a US address (everything else is optional). No price, bedroom, or room-count entry.
- **Data:** US Census Geocoder (address → ZIP, state, county) and a bundled snapshot of Zillow Research's public ZIP-level rent and home-value indexes. Tax and insurance use labeled state averages unless you enter rates.
- **Output:** for a typical home and for 1–4 bedrooms — estimated rent and three prices: **PITI break-even** (rent covers mortgage principal and interest, property tax and insurance), **all-in break-even** (also covers vacancy, management and maintenance), and **target** (meets your monthly cash-flow goal), with the monthly math, cap rate, cash-on-cash, and how the price compares with typical home values in the ZIP.
- **Not shipped:** property-level facts (list price, bedrooms, assessor records — no free national source), comparable sales, price history, projections, scores. Prices are calculations from your criteria, not appraisals or advice. See [`intent.md`](./intent.md), [`spec.md`](./spec.md), [`plan.md`](./plan.md).

## JSON API

`POST /analyze` with `Content-Type: application/json` (all `assumptions` are optional):

```json
{
  "address": "1100 Congress Ave, Austin, TX 78701",
  "assumptions": {"down_payment_pct": 20, "annual_interest_rate_pct": 7.0, "loan_term_years": 30,
                  "min_monthly_cash_flow": 100, "rent_adjustment_pct": 0,
                  "property_tax_rate_pct": 1.63, "insurance_rate_pct": 1.55, "hoa_monthly": 0}
}
```

Success: `{"success": true, "analysis": {location, market, assumptions, scenarios[], qualifier, limitations, sources}}`; each scenario has `rent`, `prices {piti_breakeven, allin_breakeven, target}`, `monthly_at_price`, and `at_target`. Every value carries `kind` (`retrieved`, `user`, `estimate`, `unavailable`) and its source or basis. Failures: `{"success": false, "error": {code, message, retryable, request_id}}` — 400 `INVALID_REQUEST`/`OUT_OF_RANGE`, 404 `PROPERTY_NOT_FOUND`, 422 `AMBIGUOUS_MATCH`/`INSUFFICIENT_DATA`, 429, 502/503/504 `PROVIDER_*`, 500. Bounds and formulas: [`spec.md`](./spec.md) §5.

## Development

```bash
make install   # one-time: .venv + dependencies
make check     # lint, format check, tests with coverage gate
make run       # dev server on http://localhost:5000
```

Contributing with an AI agent? Read [`docs/ai-sdlc.md`](./docs/ai-sdlc.md) and [`AGENTS.md`](./AGENTS.md).

## Deployment

Deployed on [Vercel](https://vercel.com) (Flask app served as a Python function; see [ADR-0004](./docs/adr/0004-deploy-on-vercel.md)). CI (`.github/workflows/ci.yml`) runs on every pull request. Setup, release, and rollback steps are in [`docs/runbook.md`](./docs/runbook.md); configuration variables are in [`.env.example`](./.env.example). A `Dockerfile` (built in CI) keeps the app portable to any container host; Procfile platforms run `gunicorn app:app`. Do not expose the Flask development server.

## How It Works
- **Address → area:** the Census Geocoder returns the standardized address and ZIP; several matches ask you to pick one.
- **Rent and value:** the ZIP's typical rent (Zillow ZORI) and typical home value (Zillow ZHVI) from `data/zip_market.json`, rebuilt monthly with `python scripts/update_market_data.py`.
- **Prices:** closed-form solver — every ownership cost except HOA scales with price, so the highest price meeting a cash-flow goal is `(income − HOA − goal) ÷ cost-per-dollar-of-price`. Prices are rounded down to $1,000.
- **Bedrooms:** typical rent × a rough heuristic factor (1BR 0.67 … 4BR 1.41); shown as low-confidence estimates.
- **Limits:** state-average tax/insurance, fixed vacancy 5% / management 8% / maintenance 1% of price per year, unknown HOA counted as $0 and flagged.

## Publishing as Mobile App
1. Deploy to an HTTPS host (this project uses Vercel)
2. Go to [PWABuilder.com](https://pwabuilder.com)
3. Enter your URL → generates iOS + Android store packages

## Important Notes
- Results describe the **area**, not a specific property; verify rents, taxes, insurance, and condition locally
- The address you enter is sent to the US Census Bureau Geocoder; nothing is stored
- Rent and home-value data: Zillow Research public indexes (attribution shown in the app)
- For informational purposes only, not financial, tax, legal, insurance, appraisal, or lending advice
