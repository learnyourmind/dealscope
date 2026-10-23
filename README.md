# DealScope — Real Estate Investment Analyzer
### Zero API keys required · Powered by Redfin public data + Python

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
pip install flask flask-cors requests
python app.py
```

## Project Status

> The feature lists below describe the **product goal**. The shipped code is smaller: `POST /analyze` returns a basic estimate (property basics, P&I, estimated rent, cash flow, cap rate, a simple verdict), `GET /healthz` reports liveness, and the web page is still a placeholder. See [`intent.md`](./intent.md) for product intent, [`spec.md`](./spec.md) for requirements and known defects, and [`plan.md`](./plan.md) for the roadmap. Numbers from the current build are estimates built on state-level averages and fallback values — not verified property facts.

## Development

```bash
make install   # one-time: .venv + dependencies
make check     # lint, format check, tests with coverage gate
make run       # dev server on http://localhost:5000
```

Contributing with an AI agent? Read [`docs/ai-sdlc.md`](./docs/ai-sdlc.md) and [`AGENTS.md`](./AGENTS.md).

## Deployment

CI (`.github/workflows/ci.yml`) runs on every pull request. The service is deployed to [Render](https://render.com) from the `Dockerfile` using `render.yaml`, and only after CI passes on `main`. Setup, release, and rollback steps are in [`docs/runbook.md`](./docs/runbook.md). Configuration variables are listed in [`.env.example`](./.env.example). Production uses Gunicorn behind the host's HTTPS; do not expose the Flask development server.

## How It Works
- **Data Engine**: Redfin's public (unofficial) API — no auth required
- **Rental Estimates**: 3-method weighted average (rent-to-price ratio, $/sqft, bedroom benchmarks)
- **Property Tax**: Built-in state-level effective rate tables (all 50 states)
- **Insurance**: Built-in state-average homeowner insurance cost tables
- **Financial Model**: Full Python model — P&I, cap rate, cash-on-cash return, NOI, GRM
- **Buy Box**: Algorithmic recommendation engine with target/max/walkaway pricing

## Analysis Output
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
1. Deploy to any free HTTPS host: [Railway](https://railway.app), [Render](https://render.com), [PythonAnywhere](https://pythonanywhere.com)
2. Go to [PWABuilder.com](https://pwabuilder.com)
3. Enter your URL → generates iOS + Android store packages

## Important Notes
- Property data accuracy depends on Redfin's public API availability
- Rental estimates are model-based; verify with local market research
- This is for informational purposes only, not professional financial advice
- Works best for US single-family residential properties
