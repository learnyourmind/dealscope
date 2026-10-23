# DealScope — Implementation Plan

**Derived from:** [`spec.md`](./spec.md) v0.2 (requirements and design) and [`intent.md`](./intent.md) (product intent).
**Process:** [`docs/ai-sdlc.md`](./docs/ai-sdlc.md) — how each task is built, verified, reviewed, and shipped.
**Rule:** if this plan and the spec disagree, the spec wins; fix the plan in the same pull request.

## How to use this plan

- Each row is one **task**: small enough for a single pull request, independently verifiable, with a test or check that proves it done.
- Status: `done` · `todo` · `blocked` (waiting on a human gate) · `later` (P1/P2, not scheduled).
- **Who**: `AI` = an AI agent can run the full loop (`/next-task`) and a human reviews the PR; `AI+H` = AI drafts, a human supplies a decision or an external action; `H` = human only (accounts, legal, brand, approvals).
- Work tasks in ID order unless **Depends** allows otherwise. Tasks with no shared dependency and no overlapping files can run in parallel (separate branches/worktrees).
- Mark a task `done` in the PR that completes it. Never mark done on the strength of "should work" — the **Done when** check must have run.

## Current state (as of this plan)

Phases D, 1, 2 and 4 are implemented, with 152 tests at 97% coverage. **Phase 4 (owner direction 2026-10-23) replaced manual entry and the Redfin adapter**: the address is the only input, data comes from the Census Geocoder and a bundled Zillow Research ZIP snapshot, and the app computes the price a rental can support. Phase 1–2 rows below that mention manual entry or the provider are historical. What remains is human work: GitHub branch protection, Vercel Git integration, the rollback rehearsal, the provider-terms decision (P0-1), brand input, and wording/privacy review; plus Phase 3 features. Baseline defects `BD-01…BD-11` (spec §2.1) are closed except `BD-09` (comps; deferred to 3.3).

## Phase D — Delivery foundation

| ID | Task | Satisfies | Depends | Who | Status | Done when |
|---|---|---|---|---|---|---|
| D1 | Repo hygiene: `.gitignore`, `ruff.toml`, `pytest.ini`, `.coveragerc`, `requirements-dev.txt`, `Makefile`, `.env.example` | OPS-06, BD-11 | — | AI | done | `make check` equivalent passes locally |
| D2 | Test scaffolding: route smoke tests; golden-vector fixture + independent spec re-derivation test | spec §5.2, §5.5 | D1 | AI | done | `pytest` green; coverage gate set at baseline |
| D3 | CI: lint, format, syntax, tests+coverage, `pip-audit`, Docker build + container smoke | OPS-01 | D1, D2 | AI | done | Workflow YAML valid; first GitHub run on PR #1: all required jobs passed |
| D4 | `Dockerfile`, `.dockerignore`, `scripts/smoke.sh`, post-deploy smoke workflow (Render blueprint dropped; hosting is Vercel, ADR-0004) | OPS-02, OPS-03, OPS-04 | D3 | AI | done | Smoke script passes against local Gunicorn; the CI `docker` job builds the image and smoke-tests the container (passed on PR #1) |
| D5 | `GET /healthz` (no upstream calls, returns version) | FR-21, OPS-04 | D2 | AI | done | `test_healthz_is_ok_and_reports_version` passes |
| D6 | Make `run.sh`/`run.bat` install from `requirements.txt` (not an ad hoc list) and fix the macOS-incompatible `hostname -I` LAN hint | BD-10 | — | AI | done | Both scripts start the app on a clean venv; no hard-coded package list |
| D7 | Push the repo, open the first PR to prove CI is green, enable **branch protection on `main`** (require the `test` and `docker` checks, require PR, no force-push) | OPS-01 | D3 | H | todo | PR shows both required checks passing; direct push to `main` rejected |
| D8 | Deploy to Vercel (done via CLI at the owner's request: https://dealscope-beige.vercel.app, smoke check passing); connect the GitHub repo in Vercel for automatic deploys from `main`; set repo variable `PROD_URL`; run the `Deployed smoke check` workflow | OPS-03, OPS-04 | D4, D5 | AI+H | partly done | Smoke workflow green against the deployed URL; Git integration connected |
| D9 | Rehearse rollback once using `docs/runbook.md` and record the time taken | OPS-05 | D8 | H | todo | Runbook updated with the observed procedure and duration |

**Phase D exit** (spec §8): D1–D9 `done`. The service is reachable only as a non-announced instance; `PROPERTY_PROVIDER` defaults to `disabled`, keeping real-provider traffic off until Phase 0 clears.

## Phase 0 — Human decisions (runs in parallel with Phase D)

These cannot be coded around. Record each outcome in spec §12 (decision log).

| ID | Decision | Blocks | Who | Status |
|---|---|---|---|---|
| P0-1 | Data-source terms. Owner chose Redfin, then redirected to free public sources (ADR-0005). Remaining: confirm Zillow Research data terms for wide/commercial use (4.6). | Wide public promotion | H | narrowed; Census use is fine |
| P0-2 | Approve or amend the proposed defaults in spec §11.1 (D-01…D-10) | 1.2, 1.3, 1.10, 2.x copy | H | approved 2026-10-23 (owner, in chat) |
| P0-3 | Brand kit, or accept the neutral fallback (spec §5.4) | 2.1 styling | H | approved 2026-10-23: neutral fallback |
| P0-4 | Privacy/retention stance for addresses in logs and the provider disclosure text | 1.9, 2.3 | H | approved 2026-10-23: as built; re-review v0.3 wording (4.7) |

## Phase 1 — Reliable analysis foundation (spec §8 Phase 1)

Target structure: `app.py` (factory + routes) and `dealscope/{errors,validation,assumptions,analysis,provider}.py` per spec §6.1. Tasks 1.1–1.4 touch disjoint files and can run in parallel after P0-2.

| ID | Task | Satisfies | Depends | Who | Status | Done when |
|---|---|---|---|---|---|---|
| 1.1 | `errors.py` + Flask error handlers + `X-Request-ID`: stable `{success:false,error:{code,message}}` envelope, status mapping per spec error table, no exception text | FR-02, FR-10, BD-04 | D2 | AI | done | Route tests: each error code returns its status and a generic message; a deliberately raised `RuntimeError("secret")` never appears in the body |
| 1.2 | `validation.py`: typed `AnalysisRequest`, bounds from spec §5.2, reject NaN/inf/wrong types/unknown keys/non-JSON | FR-02, FR-05 | P0-2 | AI+H | done | Boundary tests at each bound ±ε, `"NaN"`, `1e999`, booleans-as-numbers, 8 KB body limit |
| 1.3 | `analysis.py`: pure functions for P&I, expenses, NOI, cap rate, cash-on-cash with provenance and `unavailable` propagation | FR-06, FR-07, FR-08, spec §5.2 | P0-2 | AI | done | Reproduces `tests/fixtures/golden_vectors.json`; extra vectors for 0% rate, 100% down, zero/negative NOI, missing HOA ⇒ qualified metric; ≥ 95% coverage on the module |
| 1.4 | `assumptions.py`: move the state tables out of `app.py` with `as_of`/`source` metadata; no default-state fallback (unknown state ⇒ unavailable) | FR-09, BD-01, BD-02 | — | AI | done | Unknown/missing state returns `unavailable`, never TX constants; table-shape test (50 states + DC, rates in sane ranges) |
| 1.5 | `provider.py`: `PropertyProvider` protocol + Redfin adapter with connect/read timeouts, `raise_for_status`, size cap, malformed-payload detection, error mapping (`PROVIDER_TIMEOUT/RATE_LIMITED/UNAVAILABLE`); recorded **fixtures** in `tests/fixtures/redfin/` | FR-03, FR-04, FR-10, BD-03, BD-05 | 1.1 | AI | done | Adapter tests with `requests` mocked/fixtures: success, 404, 429, 5xx, timeout, HTML-instead-of-JSON, empty result, multiple candidates — no live calls |
| 1.6 | Structured location from the provider (state from payload, not from regex on the address); drop regex | FR-09, BD-01 | 1.5 | AI | done | Regression: `"123 Main St, Austin, TX"` resolves to `TX` from provider data; absent ⇒ `INSUFFICIENT_DATA` |
| 1.7 | Provenance model (spec §6.2) for property facts and results; remove price/sqft/beds/HOA defaults | FR-04, FR-09, BD-02 | 1.3, 1.5 | AI | done | Missing price ⇒ `INSUFFICIENT_DATA`; every output field has `kind` ∈ {retrieved,user,estimate,unavailable} |
| 1.8 | Wire `POST /analyze` to the new contract (spec §5.3): validation → provider → analysis → envelope. Ambiguity returns `AMBIGUOUS_MATCH` + candidates; analysis accepts a chosen candidate id. Restrict CORS via `CORS_ORIGINS` (default off); body-size limit; app rate limit | FR-02, FR-03, FR-10, BD-04, BD-05, BD-06 | 1.1–1.7 | AI | done | Route tests for every error code and success shape; CORS header absent by default; contract documented in README |
| 1.9 | Structured request logging (request id, route, status, latency, error code); no addresses/bodies/upstream payloads | OPS-07, spec §7 | 1.1, P0-4 | AI | done | Test captures logs for success and failure and asserts the address string is absent |
| 1.10 | Remove BUY/CAUTION. Return a neutral summary only when user criteria exist; otherwise no verdict | FR-11, BD-08 | 1.8, P0-2 | AI+H | done (wording needs human review) | No `verdict` field emitted without criteria; wording reviewed by a human |
| 1.11 | Delete dead code (`strategy`, unused imports, `math`/`datetime`); remove `app.py` entries from ruff `per-file-ignores`; reformat; raise coverage gate toward 80% | spec §5.5 | 1.8 | AI | done | `ruff check` clean with no per-file ignores; `--cov-fail-under` raised to measured floor |

**Phase 1 exit** (spec §8): tests cover success, invalid input, missing data, provider timeout, malformed response, formula edges; no live provider calls in `pytest`; spec §2.1 `BD-01…BD-09` each have a named regression test.

## Phase 2 — Usable responsive workflow

| ID | Task | Satisfies | Depends | Who | Status | Done when |
|---|---|---|---|---|---|---|
| 2.1 | `templates/index.html` + `static/app.css`/`app.js`: address form, assumptions form, disclaimer, neutral temporary design tokens; semantic HTML; works as a plain form without JS | FR-01, FR-05, FR-12, §5.4 | 1.8, P0-3 | AI | done | Page renders; form submits with JS disabled; no inline `HTML` string in `app.py` (BD-07) |
| 2.2 | Interaction states: loading (single submit), validation errors, not found, ambiguous-match chooser, provider unavailable with retry, unexpected failure; inputs preserved | FR-10, §5.4 | 2.1 | AI | done | One test or documented manual check per state in spec §5.4 |
| 2.3 | Results view: key metrics, income/expense breakdown (debt service separate from opex), provenance per value, methodology panel, limitations/missing data, provider disclosure | FR-06…FR-09, FR-12, P0-4 | 2.2 | AI+H | done | Golden-vector scenario renders the expected figures; unavailable values display as "Unavailable", not `0` |
| 2.4 | Accessibility and responsive pass: keyboard path, focus, contrast, live-region announcements, 375 px and desktop layouts; text equivalents for any chart | spec §5.4–5.5 | 2.3 | AI+H | partly done (axe clean after the fix above; manual desktop, 375 px and keyboard-only walkthrough done; **screen-reader pass still needed**) | Automated axe/Lighthouse run has no serious/critical issues; manual keyboard + screen-reader check recorded in the PR |
| 2.5 | Documentation sync: README (setup, shipped features only, limitations, test/deploy commands), `CLAUDE.md` current-state section, `intent.md` limitations list | FR-13 | 2.3 | AI | done | README claims match tested behavior; "Zero API keys" claim re-checked |
| 2.6 | Release candidate: deploy to staging/preview, run smoke + manual primary-journey test with `PROPERTY_PROVIDER=disabled` (manual entry) and, if P0-1 allows, with the live provider | spec §9 | 2.5, D8 | H | todo | Acceptance criteria 1–14 in spec §9 each checked off in the PR |

**Phase 2 exit:** a user completes the primary journey; spec §9 criteria 1–13 met; criterion 14 (provider and brand approval) recorded or listed as a deployment constraint.

## Phase 3 — Richer sourced analysis (not scheduled)

Start each only after its data rights and definitions exist (spec §8 Phase 3). One task per line; split further when scheduled.

| ID | Task | Satisfies | Status |
|---|---|---|---|
| 3.1 | Manual property entry fallback | FR-22 | done (delivered in Phases 1–2 as the launch path) |
| 3.2 | Multi-method rent estimate with ranges | FR-14 | later |
| 3.3 | Comparable sales display | FR-15, BD-09 | later |
| 3.4 | Market snapshot and price history | FR-16 | later |
| 3.5 | User-configurable buy box with target/max price | FR-17 | later |
| 3.6 | Scenario projections | FR-18 | later |
| 3.7 | Investor scores / risks & opportunities | FR-19, FR-20 | later |
| 3.8 | Staging environment gating; nightly provider-contract tests; alerting | OPS-09, OPS-10, OPS-11 | later |
| 3.9 | Pin runtime dependency versions (lockfile or `==` pins) and enable Dependabot review routine | OPS-08, spec §7 P0-7 | later (Dependabot config already added) |

## Phase 4 — Address-only buy box (owner direction 2026-10-23, spec v0.3)

| ID | Task | Satisfies | Depends | Who | Status | Done when |
|---|---|---|---|---|---|---|
| 4.1 | Replace manual entry and Redfin with Census geocoding + bundled Zillow ZIP snapshot; price solver (PITI break-even, all-in break-even, target) per bedroom scenario; remove `property`/`candidate_id` inputs | FR-02…FR-07, FR-09…FR-11, FR-22 withdrawn | — | AI | done | Solver round-trip and golden price-vector tests pass; address-only request returns prices; live Census lookup verified once manually |
| 4.2 | Redesigned UI: address-first hero, headline price, whole-home card with bars, monthly-math card, assumptions, sources, limitations; no third-party requests | FR-01, FR-05, FR-08, FR-12, §5.4 | 4.1 | AI | done | axe-core 4.10.2 on production (home and results, dark and light): one real finding (`scrollable-region-focusable` on the table wrapper), fixed; gradient-text contrast checked by hand (all ≥ 5.0:1) |
| 4.3 | Update `intent.md`, `spec.md` v0.3, README, ADR-0005, runbook | FR-13 | 4.1 | AI | done | Docs match shipped behavior |
| 4.4 | Monthly snapshot refresh: scheduled workflow runs `scripts/update_market_data.py` and opens a PR; review as-of dates | OPS-10 | 4.1 | AI+H | todo | PR opened automatically on schedule |
| 4.5 | County-level property tax (and optionally rent) from Census ACS with a free API key supplied via host secret | spec §7 | owner obtains a free key | AI+H | todo | Tax rate shown as county-level public data; fixtures from the documented ACS response shape |
| 4.6 | Confirm Zillow Research data terms for wide/commercial use | spec §7 gate | P0-1 | H | todo | Recorded in the decision log |
| 4.7 | Product/legal review of price wording ("up to", "target"); screen-reader pass | FR-11 | 4.2 | H | todo | Recorded in the decision log |
| 4.8 | Analyze one whole home as a single unit: remove the bedroom scenarios and heuristic; add `home.configuration` (`not_identified`); one-card UI | FR-06, FR-23 | 4.1 | AI | done | Tests assert no `scenarios`, no per-bedroom text, configuration unavailable; UI checked in the browser |
| 4.9 | Identify the home's configuration and rent from RentCast: adapter, graceful fallback, UI, tests (fixtures follow the documented response shape) | FR-23, FR-14 | owner chose RentCast | AI | done (not exercised live: no key yet) | 183 tests including adapter, fallback, and UI cases; key never in logs or repr |
| 4.10 | **Owner:** create a free RentCast key, add it to Vercel as a Sensitive variable `RENTCAST_API_KEY`, cap or disable overage billing, read RentCast's terms for public display/caching; then run one live lookup and compare with a known home | FR-23, spec §7 gate | 4.9 | H | todo | Live address shows `This home` with bedrooms/baths/size; usage visible in the RentCast dashboard |
| 4.11 | Optional: the home's own property tax from RentCast county records (second request per analysis, halves the free quota) | spec §7 | 4.10 | AI+H | later | Tax shown as derived from records |

## Cross-cutting definition of done (every task)

1. The test(s) named in **Done when** exist, failed before the change, and pass now.
2. `make check` passes; CI is green on the pull request.
3. No new live-network dependency in tests; no secrets, real addresses, or upstream payloads committed.
4. `spec.md` updated if a requirement, formula, bound, or decision changed; `README.md` updated if user-visible behavior or setup changed.
5. The PR template is filled in, including the AI-assistance section.

## Risks to the schedule

| Risk | Effect | Mitigation |
|---|---|---|
| Zillow Research terms do not permit wide or commercial use | Rent/value snapshot must be replaced | Sources sit behind `MarketData`; swap in a permitted ZIP rent source (4.6) |
| Redfin payload shape differs from assumptions in 1.5 | Adapter rework | Capture a few real responses **only if P0-1 permits**, scrub, store as fixtures; otherwise write fixtures from the field names already used in `app.py` and mark them synthetic |
| Serverless cold starts on Vercel | Slow first request, smoke retries | `smoke.sh` retries; note in runbook |
| Spec defaults (§11.1) change after Phase 1 | Rework in 1.2/1.3/1.10 | Keep bounds and assumptions in one module each; golden vectors are data, not code |
