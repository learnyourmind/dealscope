# DealScope — Real Estate Investment Analyzer
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

> The feature lists further down describe the **product goal**. What ships today:
> - A responsive, keyboard-accessible page at `/`: enter an address, financing assumptions, and the property's price, bedrooms, and state. (Automatic property lookup is **off by default**; see Limitations.)
> - Estimated rent, a monthly income/expense breakdown (debt service kept separate), NOI, cash flow, cap rate, and cash-on-cash return, each labeled *retrieved*, *you entered*, *estimate*, or *unavailable*, with its basis.
> - A JSON API, `POST /analyze`, and `GET /healthz`.
> - **No** market snapshot, price history, comparable sales, projections, investor scores, buy-box pricing, or buy/sell recommendation yet. See [`plan.md`](./plan.md).
>
> Tax, insurance, and rent use rough state-level constants, not quotes for the property. Treat every number as an estimate. See [`intent.md`](./intent.md) and [`spec.md`](./spec.md).

## JSON API

`POST /analyze` with `Content-Type: application/json`:

```json
{
  "address": "100 Example St, Austin, TX",
  "property": {"purchase_price": 400000, "beds": 3, "state": "TX", "hoa_monthly": 0},
  "assumptions": {"down_payment_pct": 20, "annual_interest_rate_pct": 7.0, "loan_term_years": 30, "monthly_rent": 2800}
}
```

`property` is required while automatic lookup is disabled; `hoa_monthly` and `monthly_rent` are optional (omit HOA to mark results qualified; omit rent to use the model estimate). Bounds are in [`spec.md`](./spec.md) §5.2. Success returns `{"success": true, "analysis": {property, assumptions, financing, breakdown, metrics, limitations}}` where every value carries `kind` and its basis or source. Failures return `{"success": false, "error": {code, message, retryable, request_id}}` with the HTTP status from the spec's error table (400 `INVALID_REQUEST`/`OUT_OF_RANGE`, 404 `PROPERTY_NOT_FOUND`, 422 `AMBIGUOUS_MATCH`/`INSUFFICIENT_DATA`, 429, 502/503/504 `PROVIDER_*`, 500).

## Development

```bash
make install   # one-time: .venv + dependencies
make check     # lint, format check, tests with coverage gate
make run       # dev server on http://localhost:5000
```

Contributing with an AI agent? Read [`docs/ai-sdlc.md`](./docs/ai-sdlc.md) and [`AGENTS.md`](./AGENTS.md).

## Deployment

Deployed on [Vercel](https://vercel.com) (Flask app served as a Python function; see [ADR-0004](./docs/adr/0004-deploy-on-vercel.md)). CI (`.github/workflows/ci.yml`) runs on every pull request. Setup, release, and rollback steps are in [`docs/runbook.md`](./docs/runbook.md); configuration variables are in [`.env.example`](./.env.example). A `Dockerfile` (built in CI) keeps the app portable to any container host; Procfile platforms run `gunicorn app:app`. Do not expose the Flask development server.

## How It Works (as shipped)
- **Property facts**: entered by you (default) or, if the provider is enabled, retrieved from an adapter for Redfin's unofficial endpoints (untested against the live service; needs a terms review)
- **Rent estimate**: one blended model estimate (rent-to-price ratio and bedroom benchmark, state-level), rounded to $25, or your own number
- **Property tax and insurance**: state-average rate tables (unverified prototype constants), clearly labeled as low-confidence estimates
- **Financial model**: P&I (15/20/30-year), vacancy, management, CapEx reserve, NOI, cash flow, cap rate, cash-on-cash (down payment only)
- **No recommendation**: the app shows figures and limitations; it does not say buy or pass

## Planned analysis output (goal; most items not yet implemented)
- Property details (beds, baths, sqft, year built, HOA)
- Market snapshot (median price, YoY, inventory, DOM, market type)
- Full monthly financial breakdown (P&I, tax, insurance, CapEx, vacancy, management)
- Rental analysis (estimate, range, breakeven, cash flow, cap rate, CoC return)
- Comparable sales from Redfin
- Price history
- Investor scores (cash flow, appreciation, location, risk)
- Buy box: target offer, max offer, walk-away price, 5/10-year projections
- Expert recommendation with specific numbers
- Key risks & opportunities

## Publishing as Mobile App
1. Deploy to an HTTPS host (this project uses Vercel)
2. Go to [PWABuilder.com](https://pwabuilder.com)
3. Enter your URL → generates iOS + Android store packages

## Important Notes
- With lookup disabled, property facts are whatever you enter; with it enabled, accuracy depends on the unofficial Redfin endpoints
- Rental estimates are model-based; verify with local market research
- This is for informational purposes only, not professional financial advice
- Works best for US single-family residential properties
