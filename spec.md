# DealScope — Product Requirements and Design Specification

**Version:** 0.2  
**Status:** Baseline for engineering planning. Product decisions in §11.1 are *proposed defaults* that unblock engineering; they are not owner-approved until marked so in the decision log.  
**Source of truth:** `intent.md` for product intent; this document translates that intent into requirements and design for the current repository. `plan.md` sequences the work; `docs/ai-sdlc.md` defines how it is built, verified, and deployed.  
**Product:** DealScope, a first-pass US residential rental-property analysis tool  
**Current implementation:** Flask application in `app.py`; current UI is a placeholder.

**How to read this document.** Requirement IDs (`FR-`, `OPS-`) are stable and are referenced by `plan.md` tasks and by test names. Numbers marked *proposed* are starting values to be validated by tests or product review; changing one requires a decision-log entry (§12). RFC-style words: **must** = required for the stated priority, **should** = expected unless a reason is recorded, **may** = optional.

## 1. Executive summary

DealScope should let a prospective residential property investor enter an address, review available property information, adjust a small set of assumptions, and understand an explainable estimate of rental economics and purchase viability.

The implementation should evolve the existing Flask application incrementally. The first release should deliver a working, accessible address-to-analysis flow and trustworthy estimates before attempting advanced market data, long-term projections, investor scores, or AI-generated analysis. Every reported number must be traceable to a source or stated assumption. Missing or unavailable data must not silently become a successful-looking property analysis.

This is an informational decision-support product. It must not promise returns, present estimates as quotes or verified facts, or imply that a BUY/CAUTION label is personalized financial advice.

## 2. Repository baseline

The repository currently contains:

- `app.py`: Flask routes, inline HTML placeholder, Redfin unofficial endpoint client, regional assumption tables, and a minimal analysis calculation.
- `README.md`: setup steps and a feature list that substantially exceeds the functionality implemented in `app.py`.
- `requirements.txt`: Flask, Flask-CORS, Requests, and Gunicorn.
- `run.sh`, `run.bat`, and `Procfile`: local startup and Gunicorn deployment commands.
- `CLAUDE.md` and `intent.md`: engineering and product intent guidance.

There is no test suite, database, standalone frontend, brand system, or documented deployment/security policy. The current `/analyze` route accepts JSON and returns a small set of calculated values; `GET /` renders placeholder HTML. Redfin data retrieval has no explicit timeouts or HTTP status checks, and the route catches all exceptions and exposes the exception text to clients. The analysis uses fallback property values and state-level approximations that can obscure missing data.

Treat the richer feature list in `README.md` as a product aspiration, not an existing implementation contract. As work ships, update the README to match actual functionality.

### 2.1 Known baseline defects

Found by reading `app.py` (version control history shows an earlier 1,300-line `app.py` whose UI was removed in commit `71aa9f7`; it is not a requirements source). Each defect is closed by a `plan.md` task and must gain a regression test.

| ID | Defect in current code | Consequence | Spec ref |
|---|---|---|---|
| BD-01 | State is parsed with `re.search(r"\b([A-Z]{2})\b", address.upper())`. `"123 Main St, Austin, TX"` yields `ST`, not `TX` (verified). Unknown state then falls back to default tax/insurance/rent constants. | Wrong tax, insurance, and rent for most street addresses. | FR-09, §5.2 |
| BD-02 | Missing price → `400000`, missing sqft → `1800`, missing beds → `3`, missing HOA → `0`, unknown state → `TX`/constants, all without disclosure. | Fabricated property facts shown as a successful analysis. | FR-04, FR-09 |
| BD-03 | `search`/`get_details` use no timeout and no `raise_for_status`; `_json` swallows every error with bare `except` and returns `{}`. | Hung workers; upstream failure indistinguishable from "not found". | FR-10, §7 P0-2 |
| BD-04 | `analyze_route` returns `str(e)` for every exception, and `request.get_json()` on a non-JSON body raises. | Internal text leaks to clients; all failures are HTTP 400. | FR-02, §5.3 |
| BD-05 | `search` returns `exactMatch` or the first row without ambiguity handling. | An arbitrary candidate may be analyzed. | FR-03 |
| BD-06 | `CORS(app)` allows every origin; app binds `0.0.0.0` when run directly. | Unneeded cross-origin exposure. | §7 P0-4 |
| BD-07 | `HTML` is the string `"...[Your original HTML content here]..."`, defined after its first use in `index()`. | No usable UI. | FR-01 |
| BD-08 | `strategy` is read but unused; the BUY/CAUTION verdict is `cf > 0`. | Unexplained recommendation. | FR-11 |
| BD-09 | Reduced comps are fetched (`numComps: 6`) but dropped from the response. | Wasted upstream call until FR-15 ships. | FR-15 |
| BD-10 | `run.sh`/`run.bat` install an unpinned package list that omits `gunicorn`; `run.sh` uses Linux-only `hostname -I`. | Drift from `requirements.txt`; broken LAN hint on macOS. | §5.5 Compatibility |
| BD-11 | At baseline there was no `.gitignore`, test suite, CI, health endpoint, or deploy configuration. | Nothing guarded regressions or deployment. Addressed by Phase D (`plan.md` D1–D5); remaining human steps are D7–D9. | §5.6 |

## 3. Product goals and non-goals

### 3.1 Goals

1. Provide a usable first-pass property analysis workflow for US residential rental investors.
2. Make property facts, user assumptions, and model estimates distinguishable.
3. Show the financial inputs and calculations behind important metrics and recommendations.
4. Clearly communicate uncertainty, data freshness, and limitations.
5. Handle invalid input and upstream data failures visibly without fabricating a result.
6. Build a maintainable foundation for later market context, comparable sales, price history, and projections.

### 3.2 Non-goals for the initial release

- Investment execution, financing applications, rent collection, property management, or transaction services.
- Tax, legal, insurance, appraisal, or lending advice.
- Guaranteed accuracy, predicted returns, or a guarantee that a property is a good investment.
- User accounts, saved portfolios, sharing, multi-property workflows, or persistent personal data.
- AI-generated investment recommendations. Do not add an LLM dependency or send property/user data to an AI provider as part of this specification.
- Native mobile applications. The responsive web experience is the initial target.

## 4. Target users and primary journey

### Primary user

An individual investor screening a US residential property before deciding whether to conduct deeper due diligence.

### Primary journey

1. The user opens DealScope and understands what the tool does and does not do.
2. The user enters a US property address.
3. The system searches its configured property-data source and presents a selection when the match is ambiguous.
4. The user confirms the property and reviews any retrieved property facts and their source/freshness.
5. The user reviews or changes financing assumptions, initially down-payment percentage and annual interest rate.
6. The user runs an analysis.
7. The result presents the estimated rent, monthly operating costs, financing costs, cash flow, NOI, cap rate, and cash-on-cash return where the inputs support calculation.
8. The user can inspect assumptions, missing data, formula explanations, and limitations before deciding whether to investigate further.

On an upstream failure or unusable property record, the user receives a clear retryable error and retains their entered assumptions. A partial analysis is only allowed when each omitted or estimated value is clearly identified and the affected metrics are adjusted or withheld.

## 5. Requirements

Priority definitions: **P0** required for the initial usable release; **P1** planned next; **P2** later / conditional.

### 5.1 Product and functional requirements

| ID | Priority | Requirement |
|---|---|---|
| FR-01 | P0 | Provide a responsive landing/analysis page with address input, brief product explanation, and visible informational-use disclaimer. |
| FR-02 | P0 | Validate submitted address and analysis assumptions on the server. Reject missing, wrong-type, non-finite, or out-of-range values with a useful client-safe error. |
| FR-03 | P0 | Search for a property using a data provider behind a replaceable provider boundary. Present a user confirmation/selection if the provider returns ambiguous candidates; do not silently analyze an arbitrary first result. |
| FR-04 | P0 | Retrieve property facts required for analysis and track their source, retrieval time, and whether a value is reported, user-provided, or estimated. |
| FR-05 | P0 | Provide an assumptions form for down-payment percentage and annual interest rate. Preserve submitted values through validation and upstream errors. Define sensible bounds in implementation and test their edges. |
| FR-06 | P0 | Calculate and display purchase price, down-payment amount, loan amount, monthly principal and interest, estimated monthly rent, operating expenses, NOI, monthly cash flow, cap rate, and cash-on-cash return only when required inputs exist. |
| FR-07 | P0 | Show a categorized monthly expense breakdown. Clearly separate operating expenses from debt service; do not include principal and interest in NOI or cap-rate calculation. |
| FR-08 | P0 | Explain each estimate and financial metric through visible labels, a concise methodology explanation, and an assumptions/source detail area. Include units and time period. |
| FR-09 | P0 | Mark unavailable data as unavailable. Do not substitute invented property details, a default state, or a plausible-looking price without an explicit, disclosed assumption and user confirmation. |
| FR-10 | P0 | Handle property not found, ambiguous match, upstream timeout/rate limit/unavailability, malformed upstream response, and internal failure as distinct user-safe states. |
| FR-11 | P0 | Provide a recommendation state only when its decision rule is documented and inputs are adequate. Explain its threshold and basis. Prefer a neutral “meets/does not meet your criteria” framing over an unconditional “BUY” instruction. |
| FR-12 | P0 | State clearly that estimates are for informational purposes, not professional financial, tax, legal, insurance, appraisal, or lending advice. Encourage local verification. |
| FR-13 | P0 | Update README setup and feature descriptions when the usable interface or analysis output changes. |
| FR-14 | P1 | Expand rental estimation into multiple documented methods, including rent-to-price, bedroom/market benchmark, and price-per-square-foot when credible inputs exist. Show method contributions and uncertainty; do not imply calibration where none exists. |
| FR-15 | P1 | Add comparable sales when provider data is available, with dates, distance/context when supplied, and source attribution. Do not describe asking/list prices as verified sale prices unless provider fields confirm that meaning. |
| FR-16 | P1 | Add market snapshot and price-history displays only when data, definitions, time coverage, and provenance are available. |
| FR-17 | P1 | Add an investor buy box with user-configurable criteria and calculated target/maximum price. Avoid fixed unexplained verdict thresholds. |
| FR-18 | P2 | Add five-/ten-year scenario projections only after assumptions for rent growth, appreciation, expense growth, sale costs, and financing are specified and user-visible. Use scenarios, not predictions. |
| FR-19 | P2 | Add investor scores only if their inputs, weighting, interpretation, and limitations can be explained; scores must not conceal missing data. |
| FR-20 | P2 | Add risk/opportunity summaries based on traceable data or explicit rules. No unsupported “expert” claims. |
| FR-21 | P0 | Expose `GET /healthz` returning `200 {"status":"ok","version":"<app version>"}` without calling any upstream provider, for deployment health checks (see OPS-04). |
| FR-22 | P1 | When the provider is unavailable or returns insufficient data, let the user enter price, beds, and state manually; such values are classified as user assumptions (§5.2) and the result is labeled as based on user-entered facts. |

### 5.2 Data and calculation requirements

#### Data classification

Every analysis input must be classified as one of:

- **Retrieved fact:** value returned by the provider, with provider/source and retrieval timestamp.
- **User assumption:** value entered or explicitly accepted by the user.
- **Model estimate:** value derived from a documented formula or an identified benchmark.
- **Unavailable:** value not obtained or not reliable enough to use.

The API/UI must preserve this classification rather than flattening all values into indistinguishable numbers.

#### Financial definitions

The implementation must document formulas in code and user-facing methodology text. At minimum:

- `loan_amount = purchase_price - down_payment`
- Monthly principal and interest is calculated from loan amount, annual nominal interest rate, and a stated term (initial proposal: 30 years; confirm in product requirements before release if the term is user-adjustable).
- `effective_rent = gross_monthly_rent × (1 - vacancy_rate)`
- Operating expenses include applicable property tax, insurance, HOA, maintenance/CapEx reserve, and management expense. Any excluded category must be named.
- `NOI = effective_rent - monthly_operating_expenses`; debt service is excluded.
- `monthly_cash_flow = NOI - monthly_principal_and_interest`
- `cap_rate = annual_NOI / purchase_price × 100`
- `cash_on_cash_return = annual_pre_tax_cash_flow / cash_invested × 100`; disclose which upfront costs are included in cash invested. If closing costs or reserves are unknown, either exclude them explicitly or withhold/qualify the metric.

The existing use of a single fixed state-level estimate and silent property fallbacks is not sufficient for a production-quality recommendation. Initial regional benchmarks may remain if they are labeled, versioned/documented, and explicitly shown as estimates. Values without a defensible source should be omitted or require user entry.

#### Input bounds (proposed)

Enforced server-side (FR-02); the UI mirrors them for convenience but is never the only check. Out-of-range values are rejected, never clamped.

| Input | Type | Bounds | Default |
|---|---|---|---|
| `address` | string | trimmed length 5–200; no control characters | required |
| `down_payment_pct` | number | 5 ≤ x ≤ 100 (investor financing rarely goes below 15–25%; 5 is a permissive floor) | 20 |
| `annual_interest_rate_pct` | number | 0 ≤ x ≤ 25; finite | 7.0 |
| `loan_term_years` | integer | one of 15, 20, 30 | 30 |

`down_payment_pct = 100` gives a zero loan: principal and interest is `0`, not a division error. `annual_interest_rate_pct = 0` divides the loan evenly over the term.

#### Default operating assumptions (proposed)

These carry over from the current code and must be labeled *model estimate* (editable by the user from FR-17 onward). Rates are per-month figures derived from annual values.

| Item | Rule | Source in current code |
|---|---|---|
| Vacancy | 5% of gross monthly rent | `rent * 0.05` |
| Management | 8% of gross monthly rent | `rent * 0.08` |
| Maintenance / CapEx reserve | 1% of purchase price per year ÷ 12 | `price * 0.01 / 12` |
| Property tax | state effective rate × price ÷ 12 | `TAX_RATES` table (state average, **not** property-specific) |
| Insurance | state average rate × price ÷ 12 | `INS_RATES` table (state average) |
| HOA | provider-reported monthly value; if absent, *unavailable* — metrics are qualified, not silently zeroed | `hoa or 0` (BD-02) |

Rent estimate (P0): the existing blend of rent-to-price ratio and bedroom benchmark scaled by `STATE_COST`, rounded to the nearest $25, labeled *model estimate* and shown with an explicit "state-level benchmark, not a market quote" note. It is withheld when state or bedroom count is unavailable. P1 (FR-14) replaces it with documented multi-method estimates.

#### Golden test vector

Used verbatim as a unit test for the calculation module. Inputs are explicit so the test needs no provider.

| Input | Value |
|---|---|
| purchase price | $400,000 |
| down payment | 20% → $80,000 |
| rate / term | 7.0% / 30 years |
| gross monthly rent | $2,800 |
| property tax rate / insurance rate | 1.63% / 1.55% of price per year |
| HOA | $0 (reported) |

| Output | Expected (monthly unless noted) |
|---|---|
| loan amount | $320,000 |
| principal and interest | $2,128.97 |
| property tax / insurance | $543.33 / $516.67 |
| CapEx reserve / vacancy / management | $333.33 / $140.00 / $224.00 |
| operating expenses | $1,757.33 |
| NOI | $1,042.67 |
| cash flow (NOI − P&I) | −$1,086.30 |
| cap rate (annual NOI ÷ price) | 3.13% |
| cash-on-cash (annual cash flow ÷ down payment only) | −16.29% |

Tests compare currency to the cent and percentages to two decimals. Additional vectors must cover 0% interest, 100% down, zero/negative NOI, and missing HOA (metric qualified).

#### Recommendation policy

The intent asks for explainable recommendations and buy-box pricing but does not define investment criteria. Before implementing thresholds, product must specify whether a recommendation is based on user-defined criteria, a transparent default buy box, or both. Until then:

- Do not use an unexplained BUY/CAUTION label.
- Do not present a single score as an investment decision.
- A neutral summary may report whether user-provided targets are met, with the criteria and values beside it.

### 5.3 API requirements

The current endpoint is `POST /analyze`; the following contract is a target, not a promise of backward compatibility. Keep the browser/API integration internally consistent. If external consumers exist, version the API before breaking the current shape.

#### Request (proposed)

```json
{
  "address": "123 Main St, Austin, TX",
  "assumptions": {
    "down_payment_pct": 20,
    "annual_interest_rate_pct": 7.0,
    "loan_term_years": 30
  }
}
```

The server must validate JSON type, required fields, string length, numeric finiteness, and documented bounds. Never accept provider URLs or arbitrary network targets from the client.

#### Success response (proposed shape)

```json
{
  "success": true,
  "analysis": {
    "property": {
      "address": {"value": "123 Main St, Austin, TX", "kind": "retrieved", "source": "provider", "retrieved_at": "ISO-8601 timestamp"},
      "purchase_price": {"value": 400000, "unit": "USD", "kind": "retrieved", "source": "provider", "retrieved_at": "ISO-8601 timestamp"},
      "beds": {"value": 3, "unit": "bedrooms", "kind": "retrieved", "source": "provider", "retrieved_at": "ISO-8601 timestamp"}
    },
    "assumptions": {},
    "metrics": {},
    "limitations": []
  }
}
```

This is an illustrative shape. Define complete schemas and required fields in implementation; do not return placeholder values such as `"provider"` as literal provenance.

#### Error response (proposed shape)

```json
{
  "success": false,
  "error": {
    "code": "PROPERTY_NOT_FOUND",
    "message": "We couldn't find a matching property. Check the address and try again."
  }
}
```

Use appropriate HTTP status codes (for example 400 for invalid input, 404 for no match, 422 for ambiguous selection if modeled that way, 502/503 for provider failures, and 500 for unexpected server errors). Do not return exception text, stack traces, upstream response bodies, or internal implementation details to the client. Log safe diagnostic details server-side without sensitive request bodies.

#### Error codes (proposed)

| Code | HTTP | Meaning | Retryable |
|---|---|---|---|
| `INVALID_REQUEST` | 400 | Malformed JSON, wrong content type, unknown or missing field, wrong type | no |
| `OUT_OF_RANGE` | 400 | Value outside §5.2 bounds; response names the field, not internals | no |
| `PROPERTY_NOT_FOUND` | 404 | Provider answered successfully with no match | no |
| `AMBIGUOUS_MATCH` | 422 | Several candidates; body includes `candidates` (id, display address) for selection | no |
| `INSUFFICIENT_DATA` | 422 | Match found but required facts (price, beds, state) are unavailable | no (FR-22 offers manual entry) |
| `PROVIDER_TIMEOUT` | 504 | Upstream exceeded the §5.5 timeout | yes |
| `PROVIDER_RATE_LIMITED` | 503 | Upstream returned 429/403-style throttling; include `Retry-After` only if the provider supplied it | yes, later |
| `PROVIDER_UNAVAILABLE` | 502 | Upstream 5xx, connection failure, or malformed/unrecognized payload | yes |
| `RATE_LIMITED` | 429 | This app's own per-client limit (§7 P0-8) | yes |
| `INTERNAL_ERROR` | 500 | Unexpected failure; message is generic, a `request_id` is returned and logged | yes |

Every response carries an `X-Request-ID` header (generated if absent) that is also written to server logs. `GET /healthz` is exempt from the envelope and from rate limiting.

### 5.4 User experience and visual design requirements

#### Information architecture

Initial page:

1. Product name and short purpose statement.
2. Address search field and primary action.
3. Short note on estimates and data availability.
4. Prominent but concise informational-use notice.

Analysis page/state:

1. Property identity, matching confidence/selection, and data freshness.
2. Key result summary: estimated rent, monthly cash flow, NOI, and cap rate.
3. Financing assumptions with editable controls and an explicit recalculate action or clear immediate-update behavior.
4. Monthly income and expense breakdown.
5. Calculation/methodology and provenance details.
6. Missing data, limitations, and due-diligence reminders.
7. Comparable/market sections only when implemented and populated from a source.

#### Interaction states

Design and implement: initial, submitting/loading, property not found, ambiguous match, analysis success, partial data, invalid input, provider unavailable/rate limited, retry, and unexpected failure. Prevent duplicate accidental submissions where appropriate. Retain user inputs on recoverable errors.

#### Visual and interaction standards

- Use plain-language labels and familiar financial terminology; define acronyms such as NOI on first use.
- Use US currency formatting consistently; show whether values are monthly or annual.
- Do not convey positive/negative status by color alone; pair color with text/icon/meaning.
- Keep the primary action visually clear and keyboard accessible.
- Ensure responsive layouts at mobile and desktop sizes, semantic headings/forms, visible focus, sufficient contrast, and accessible error announcements.
- Do not use urgency, celebratory investment language, guaranteed-return framing, or coercive prompts.
- Treat charts as optional enhancements; provide equivalent values and explanations in accessible text/table form.

#### Brand limitation and proposed fallback

No formal brand guide, approved logo, color palette, typography, voice/tone guide, or design tokens are present in the repository. The only identity evidence is the DealScope name and the house emoji used by the shell startup script; that is not sufficient to infer a complete visual identity.

Therefore this specification cannot certify conformance to brand guidelines. Until an owner supplies approved assets/tokens, use a restrained, neutral, high-contrast financial-tool presentation; retain the DealScope name; avoid inventing a logo, brand colors, or marketing claims. Record the temporary design tokens in the UI implementation and replace them with approved tokens once provided. Product/design approval is required before claiming formal brand compliance.

### 5.5 Non-functional requirements

- **Reliability:** Bound upstream call duration; distinguish provider errors from valid empty results. Avoid returning stale or fallback values as current data.
- **Performance:** Show loading feedback; set an explicit request timeout and enforce an overall reasonable request budget. The initial threshold should be measured in testing and adjusted using observed provider latency.
- **Accessibility:** Target WCAG 2.2 AA for the delivered web workflow, including keyboard use, focus indication, contrast, labels, and screen-reader error/status announcements.
- **Maintainability:** Isolate provider access, validation, financial calculations, and presentation sufficiently to test without live Redfin requests. Avoid expanding `app.py` into a monolith.
- **Compatibility:** Keep existing run scripts, `requirements.txt`, and `Procfile` consistent with app changes. Support the Python versions chosen for deployment and document them.
- **Observability:** Log request outcomes, provider failures, and latency with safe correlation identifiers; do not log unnecessary personal/address data or upstream payloads.
- **Documentation:** README must describe shipped behavior, dependencies, startup, provider limitations, and financial disclaimers.
- **Testing:** Add automated tests for input validation, financial formulas, provider response parsing, route status/response shapes, and key UI states. Unit tests must not depend on live provider availability.

#### Numeric targets (proposed; validate against observed provider latency)

| Target | Value |
|---|---|
| Per-upstream-call timeout | connect 3 s, read 8 s |
| Overall analysis budget | 15 s (return `PROVIDER_TIMEOUT` rather than wait longer) |
| Gunicorn worker timeout | 30 s |
| Request body limit | 8 KB |
| Own rate limit before public launch | 20 analyses/min/IP, burst 5 (or enforced at the host edge) |
| Calculation module | pure functions, no I/O, no global state; ≥ 95% line coverage |
| Overall test coverage gate in CI | Ratchet: starts just below the measured baseline (46% when adopted → gate 40%) and is raised with each Phase 1 task; target ≥ 80% lines by the end of Phase 1 |

### 5.6 Delivery and operations requirements

| ID | Priority | Requirement |
|---|---|---|
| OPS-01 | P0 | Every change reaches `main` through a pull request whose CI run passes: lint, format check, tests with the coverage gate, and dependency vulnerability audit. `main` is protected against direct pushes and failing checks. |
| OPS-02 | P0 | The app builds into a container image from a checked-in `Dockerfile`: non-root user, pinned Python minor version, runs Gunicorn bound to `$PORT`, contains no secrets, and has a `HEALTHCHECK` on `/healthz`. |
| OPS-03 | P0 | Deployment is declarative (`render.yaml` for the chosen host, §6.4) and automatic from `main` only after CI passes. Production is HTTPS-only. |
| OPS-04 | P0 | A post-deploy smoke check calls `GET /healthz` and `GET /` and fails the release if either is not 200. |
| OPS-05 | P0 | Rollback to the previous release is documented in `docs/runbook.md` and achievable in minutes without a code change (host "redeploy previous" or git revert). |
| OPS-06 | P0 | Configuration is environment-driven (§6.3); `.env.example` lists every variable without secret values; `.env` is git-ignored. |
| OPS-07 | P0 | Logs are structured one-line records to stdout with `request_id`, route, status, latency, and error code; they exclude addresses, request bodies, and upstream payloads (§7 Privacy). |
| OPS-08 | P1 | Dependency updates arrive as automated pull requests (Dependabot) and pass the same CI gates. |
| OPS-09 | P1 | A gated *staging* environment (or Render preview environments) runs the smoke check before production promotion. |
| OPS-10 | P1 | Provider-contract tests replay recorded fixtures of Redfin payloads and run nightly against the live provider **only if** Phase 0 approves such use; failure opens an issue rather than blocking unrelated pull requests. |
| OPS-11 | P2 | Alerting on elevated 5xx or `PROVIDER_*` rates and on `/healthz` failure. |

## 6. Proposed architecture

Preserve Flask and avoid introducing a frontend framework, database, or AI service for the initial release. As the implementation grows, extract responsibilities from `app.py` into small modules following the repository's Python packaging conventions. A possible structure:

```text
app.py                  # Flask app creation and route registration
dealscope/
  provider.py           # Provider interface and Redfin adapter
  analysis.py           # Typed input/output models and financial calculations
  validation.py         # Request validation and bounds
  errors.py             # Safe domain/provider error mapping
templates/
  index.html            # Server-rendered page
static/
  app.css
  app.js
tests/
  test_analysis.py
  test_routes.py
  test_provider.py
```

This is a target organization, not a required directory layout. Adopt only as needed. A small provider interface should make test doubles and future licensed data providers possible without allowing the UI or calculation logic to depend on Redfin response internals.

#### Request flow

Browser form → Flask route → validated request model → property provider → normalized property facts/provenance → deterministic analysis service → JSON or server-rendered result → UI.

Provider responses must be normalized at the boundary. Calculations must operate on normalized, typed values, not nested vendor JSON. Provider failure must not be hidden by fabricated property defaults.

### 6.1 Component responsibilities

| Component | Responsibility | Must not |
|---|---|---|
| `app.py` | Create the Flask app (`create_app()` factory plus module-level `app` for Gunicorn), register routes, error handlers, request-ID and logging middleware | Contain calculations, vendor JSON parsing, or HTML |
| `dealscope/validation.py` | Parse and validate the request into a typed `AnalysisRequest`; raise `ValidationError(code, field)` | Touch the network |
| `dealscope/provider.py` | `PropertyProvider` protocol (`search(address) -> list[Candidate]`, `get_property(candidate_id) -> PropertyFacts`) and the Redfin adapter; applies §5.5 timeouts, maps HTTP and parse failures to `ProviderError` subclasses | Return vendor JSON, apply defaults, or compute metrics |
| `dealscope/analysis.py` | Pure functions: mortgage payment, expenses, NOI, cap rate, cash-on-cash; returns values with `kind`/provenance and explicit `unavailable` markers | Perform I/O or read globals other than versioned assumption tables |
| `dealscope/assumptions.py` | State tables and default rates, each with `as_of`/`source` metadata | Be imported by the provider layer |
| `dealscope/errors.py` | Domain exceptions → (code, HTTP status, safe message) | Include exception text in messages |
| `templates/`, `static/` | Accessible UI (§5.4), progressive enhancement over a plain form POST | Compute financial values client-side |
| `tests/` | Unit, route, and fixture-based provider tests; no live network | Depend on Redfin availability |

### 6.2 Provenance model

Every value in `analysis.property`, `analysis.assumptions`, and `analysis.metrics` is an object:

```json
{"value": 543.33, "unit": "USD/month", "kind": "estimate", "basis": "TX state effective rate 1.63% × price ÷ 12", "as_of": "2026-01 table", "confidence": "low"}
```

`kind` ∈ `retrieved | user | estimate | unavailable`. Retrieved values carry `source` and `retrieved_at`; estimates carry `basis` and the table `as_of`; unavailable values carry `reason` and no `value`. A metric whose inputs include an `unavailable` value is itself `unavailable` or carries `qualified: true` with the names of the missing inputs. `source` is a real provider identifier from configuration, never the literal word "provider".

### 6.3 Configuration (environment variables)

| Variable | Default | Purpose |
|---|---|---|
| `PORT` | `5000` | Listen port (set by the host) |
| `APP_ENV` | `development` | `production` disables debug-only behavior |
| `CORS_ORIGINS` | empty (CORS off) | Comma-separated allowed origins; empty means same-origin only |
| `PROPERTY_PROVIDER` | `redfin` | Selects the adapter; `disabled` forces the manual-entry path (FR-22) |
| `UPSTREAM_CONNECT_TIMEOUT_S` / `UPSTREAM_READ_TIMEOUT_S` | `3` / `8` | §5.5 |
| `RATE_LIMIT` | `20/minute` | §5.5; empty disables (use only behind an edge limiter) |
| `LOG_LEVEL` | `INFO` | Log verbosity |
| `APP_VERSION` | `dev` | Injected at build time (git SHA); returned by `/healthz` |

No variable holds a secret in the initial release. A future licensed provider adds its key as a host-managed secret, never in the repository.

### 6.4 Deployment architecture

```text
developer / AI agent → feature branch → pull request ─► CI (lint · format · test · coverage · audit · docker build)
                                                        │ pass + review
                                                        ▼
                                                      main ─► Render (render.yaml, autoDeploy after checks)
                                                                  │  Docker image → Gunicorn → Flask
                                                                  ▼
                                              post-deploy smoke: /healthz, /   → failure ⇒ rollback (docs/runbook.md)
```

Render is the proposed first host because the README already lists it, it supports a free HTTPS web service from a Dockerfile, health-check-gated deploys, and one-click rollback. The `Dockerfile` keeps the app portable to any container host (Railway, Fly.io, Cloud Run) if the decision changes. A single instance is sufficient: the app is stateless with no database (see below), so scaling is horizontal Gunicorn workers/instances.

#### Data persistence

No database is required initially. Do not persist addresses, financial assumptions, or analysis results unless a separate product requirement, retention policy, access-control design, and deletion policy are approved. If caching is later considered, define freshness and provider terms first.

## 7. Security, privacy, and policy requirements

The following are engineering requirements for this app, not a substitute for a formal organization security policy. No separate security-policy document was found in the repository.

### P0 controls

1. **Input validation:** Require a JSON object or valid form submission, validate expected keys and types, bound address length and numeric values, reject NaN/infinity, and reject unsupported content types cleanly.
2. **Upstream request safety:** Keep provider hosts fixed in server configuration. Never fetch a URL supplied by the user. Use explicit connect/read timeouts, validate HTTP status, constrain response size where practical, and handle malformed responses.
3. **Error disclosure:** Return stable, user-safe error codes/messages. Do not expose exception strings or raw provider data. Log server-side diagnostics with appropriate redaction.
4. **CORS:** Remove global permissive `CORS(app)` unless a documented cross-origin client requires it. If required, allow only explicit configured origins and necessary methods/headers.
5. **Transport:** Production deployment must use HTTPS at the hosting layer. Do not encourage sharing the development server over an untrusted network.
6. **Secrets:** No credentials in source, templates, scripts, logs, or documentation. Configure future provider credentials through deployment environment/secrets facilities.
7. **Dependency hygiene:** Keep dependencies minimal and pinned/managed according to the project’s chosen dependency policy. Review updates for Flask, Requests, and any added packages.
8. **Request limits:** Configure a reasonable maximum request body size and avoid unbounded expensive provider calls. Add rate limiting before public exposure if the hosting environment does not provide it.
9. **Template safety:** Continue using escaped template interpolation. Do not mark user/provider strings as trusted HTML. Sanitize any future client-rendered markup.
10. **Production server:** Do not use Flask's development server in production; use the configured Gunicorn process.

### Privacy

An address can be sensitive personal or location information even though the app has no accounts. Minimize collection and retention. Disclose that the address is sent to the selected property-data provider. Avoid logging full addresses unless necessary for a documented operational purpose; define retention/access controls before retaining them.

### Provider, licensing, and data-use concern

The current code uses Redfin's unofficial public endpoints. The repository does not establish that this access is authorized for the planned use, stable, licensed for display/redistribution, or appropriate for production. Before public release or product claims based on these data:

- Review provider terms and applicable data-use restrictions.
- Confirm the right to retrieve, transform, display, cache, and attribute each data category.
- Identify a supported provider or obtain legal/product approval for continued use.
- Do not attempt to bypass access controls, rate limits, bot protections, or other provider restrictions.

This is a release gate, not something engineering can resolve by coding around provider protections. If usage rights cannot be confirmed, disable the affected data integration and provide a user-entry or alternative-provider path.

### Financial-content concern

The intent includes “recommendations,” target/max/walk-away prices, and “expert recommendation” wording. These terms can suggest individualized investment advice, especially when presented as instructions. This spec constrains output to transparent calculations and user-defined criteria and removes unsupported authority. Product/legal review is needed before using prescriptive recommendation language, personalized rankings, or claims of expertise. A disclaimer alone does not cure misleading or unsupported product behavior.

## 8. Delivery plan

`plan.md` is the executable breakdown of the phases below into ordered, independently verifiable tasks (each citing the requirement IDs it satisfies). The phases here remain the authority on scope and exit criteria; if the two disagree, fix `plan.md`.

### Phase D — delivery foundation (runs first, in parallel with Phase 0)

- Add `.gitignore`, dev tooling, test scaffolding, CI, Dockerfile, deploy blueprint, health endpoint, runbook (OPS-01 … OPS-07, FR-21).
- Deploy the *current* app (placeholder UI) to a non-public environment to prove the pipeline end to end.

**Exit criteria:** A pull request runs CI green; merge to `main` deploys to the staging/preview target; the smoke check passes; a rollback has been rehearsed once. No public announcement and no real-provider traffic before Phase 0 approval.

### Phase 0 — decisions and data foundation

- Confirm data-provider terms, display rights, and availability.
- Confirm target user, property types, supported geography, financing term, and minimum required data.
- Approve the buy-box decision policy or defer verdicts.
- Obtain brand assets/design tokens and product-approved tone, or approve the neutral temporary design fallback.
- Define initial financial assumptions and which estimates must be user-editable.

**Exit criteria:** Open issues affecting legality, data rights, core formulas, and visual identity are either resolved or explicitly accepted as release constraints.

### Phase 1 — reliable analysis foundation

- Add request validation, provider timeouts/status checks, normalized provider results, explicit domain errors, and safe HTTP error mapping.
- Remove silent defaults for missing price/state/property fields; model unavailable data.
- Extract/test financial calculation functions and correct NOI/cap-rate/cash-on-cash definitions.
- Add focused tests using mocked provider responses.
- Tighten or remove CORS according to actual client needs.

**Exit criteria:** Unit and route tests cover success, invalid input, missing data, provider timeout, provider malformed response, and formula edge cases. No live provider dependency in ordinary test runs.

### Phase 2 — usable responsive workflow

- Replace placeholder HTML with an accessible address and assumptions form.
- Implement loading, error, selection, partial-data, and results states.
- Present sourced facts, estimates, assumptions, expense breakdown, key metrics, and disclosures.
- Verify keyboard and screen-reader behavior and mobile layout.
- Update README to accurately describe the delivered experience and known limitations.

**Exit criteria:** A user can complete the primary journey locally using provider test doubles; real provider use is gated by Phase 0 approval and integration checks.

### Phase 3 — richer sourced analysis

- Add improved rental methodologies, comparable sales, market snapshot, and history only when legal data access and reliable definitions are available.
- Add user-configurable buy-box criteria and explainable matching.
- Add projections and qualitative risk summaries only after assumptions and evaluation criteria are approved.

**Exit criteria:** Every additional metric has provenance, definitions, tests, limitations, and review of how it is presented to users.

## 9. Acceptance criteria for initial release

Initial release is acceptable when:

1. The root page is a functional, responsive and keyboard-accessible interface, not placeholder text.
2. A valid address and valid assumptions can produce a normalized analysis when the provider returns sufficient data.
3. Ambiguous addresses require user selection; no arbitrary first candidate is silently analyzed.
4. Missing required data or provider failure produces an explicit, recoverable error or a clearly labeled partial analysis; it never silently receives a fabricated property value.
5. Each result value identifies whether it is retrieved, user-supplied, or estimated, and shows an applicable source/freshness or methodology.
6. Operating expenses are separate from debt service; NOI and cap rate follow the definitions in this spec.
7. Cash-on-cash return is withheld or qualified when the cash-invested denominator is incomplete.
8. Recommendations are absent until criteria are documented, or are explicitly tied to user-set criteria and explained.
9. Financial and data limitations are visible without obscuring the main result.
10. User-facing errors contain no internal exception details or raw upstream content.
11. CORS is appropriately restricted, upstream requests are bounded, and production uses HTTPS/Gunicorn.
12. Tests cover calculation formulas, validation, route response shapes, and upstream error behavior.
13. README and engineering guidance accurately describe the current application and setup.
14. Provider usage approval and brand approval are recorded, or their absence is clearly treated as a deployment constraint.
15. Delivery: CI is green and required on `main`; the container image builds and passes the smoke check; `GET /healthz` is 200; rollback has been rehearsed once and the runbook updated (OPS-01 … OPS-07).
16. Each defect `BD-01 … BD-09` in §2.1 has a regression test whose name cites its ID.

## 10. Risks, contradictions, and unresolved decisions

| Concern | Why it matters | Proposed handling / decision needed |
|---|---|---|
| No brand guidelines found | Cannot certify conformance to an absent palette, logo, typography, or voice/tone policy. | Request approved brand kit. Until supplied, use the clearly provisional neutral fallback in §5.4; do not invent brand assets. |
| No separate security or UX policy found | This spec cannot claim formal policy compliance beyond stated engineering safeguards and accessibility criteria. | Security/product owners should review §7 and §5.4 against organizational policy before public launch. |
| Redfin integration is unofficial | Production display, redistribution, availability, and access method may conflict with provider restrictions. | Legal/provider review is a Phase 0 gate. Do not bypass protections; replace or disable integration if permission is unavailable. |
| README overstates delivered functionality | Users and engineers may assume features exist when the code does not implement them. | Treat this document and actual tests/code as implementation baseline; update README as each feature ships. |
| Recommendations vs. non-advisory purpose | BUY/CAUTION and target/walk-away outputs may appear to be personalized financial advice. | Avoid imperative labels; require transparent user-set criteria and legal/product review before recommendation wording. |
| Unvalidated regional estimates | State-level averages can materially misrepresent a specific property's rent, tax, or insurance. | Label and source every estimate; show uncertainty; allow user edits; withhold unsupported metrics. |
| Current source parsing is fragile | Unofficial response shapes can change; current broad exception handling hides causes and returns exception text. | Normalize, validate, timeout, test fixtures, and map failures to safe errors. |
| State detection from address text | Parsing two-letter substrings can select the wrong state or default to Texas. | Use provider-normalized structured location; otherwise require user confirmation. Do not default a location silently. |
| No test suite or app structure | Financial regressions and provider failures are difficult to detect. | Add focused tests and incrementally separate testable calculation/provider code. |
| “Zero API keys required” marketing claim | May cease to be true if a supported/licensed provider requires credentials. | Keep README claim only while accurate; otherwise update onboarding and credential handling. |
| Proposed loan term and bounds not specified by intent | Calculations depend on these choices, and sensible bounds are product choices. | Product must approve initial loan term and input ranges before release. |
| No data retention/provider disclosure policy | Addresses may be sensitive and are sent to a third party. | Disclose provider transmission and define logs/retention before public deployment. |

## 11. Open product decisions (must resolve before relevant work)

1. What data provider is approved for property facts, rents, comparable sales, and market data, and what attribution/retention terms apply?
2. Which property types and geographies are in scope for the first production release?
3. What is the required source/quality threshold for price, rent, tax, insurance, HOA, and comparable data?
4. Should rent estimates be computed solely from provider data, from documented local benchmarks, or from user input when provider data is unavailable?
5. Which loan term and financing assumptions are defaults, and which must users be able to change?
6. Which costs count toward cash invested for cash-on-cash return?
7. What exact user-configurable criteria define the buy box? Should there be any default criteria?
8. Are market snapshots, projections, and scores required for launch, or explicitly deferred?
9. What approved brand assets, colors, typography, voice, and design tokens should the interface use?
10. What public deployment, privacy, retention, accessibility, and security review process is required?

### 11.1 Proposed defaults (to unblock engineering; status: **proposed — awaiting owner approval**)

Engineering may build to these without waiting. If the owner chooses differently, change the value here, in the decision log, and in the module that holds it (bounds in `validation.py`, assumptions in `assumptions.py`); golden vectors are data and must be updated in the same change.

| ID | Answers §11 | Proposed default | Rationale / what would change it |
|---|---|---|---|
| D-01 | #1 provider | Redfin adapter behind a `PropertyProvider` interface, **disabled in production** until terms are reviewed; manual entry (FR-22) is the fallback path | Legal review may force a different provider or manual-only |
| D-02 | #2 scope | US addresses; single-family residential only; other property types return `INSUFFICIENT_DATA` with an explanation | Current code and README target single-family |
| D-03 | #3 data quality | Price, beds, and state must be retrieved or user-entered; tax, insurance, and rent are labeled state-level estimates (low confidence); HOA absence qualifies the metric | Matches FR-09 and intent principles 1–2 |
| D-04 | #4 rent source | Model estimate (§5.2) in P0, user override allowed once FR-17 exists; no claim of market calibration | Replaced by FR-14 multi-method estimate in P1 |
| D-05 | #5 financing | Default 20% down, 7.0% rate, 30-year term; user can change down payment and rate in P0; term selectable (15/20/30) in the API from P0 and in the UI from P1 | Bounds in §5.2 |
| D-06 | #6 cash invested | Down payment only in P0; closing costs and reserves excluded and the exclusion is stated beside the metric | Add optional user-entered closing costs in P1 |
| D-07 | #7 buy box | No default verdict. User criteria (min cash flow, min cap rate, min cash-on-cash) arrive with FR-17; until then, no recommendation field | Avoids implied investment advice (§7) |
| D-08 | #8 deferred scope | Market snapshot, projections, and scores are not part of launch | FR-16, FR-18, FR-19 stay P1/P2 |
| D-09 | #9 brand | Neutral fallback design tokens (§5.4) until a brand kit is supplied | Owner supplies assets |
| D-10 | #10 review process | Pull-request review plus CI gates (OPS-01); privacy: no persistence, no address logging; accessibility target WCAG 2.2 AA | Organization may require a formal security or legal review before public launch |

## 12. Documentation and change control

### Decision log

Record each decision when made. Status: `proposed` → `approved` (by whom, when) or `rejected`.

| Date | ID | Decision | Status | Decided by |
|---|---|---|---|---|
| 2026-10-23 | D-01 … D-10 | Defaults in §11.1 | proposed | — |
| 2026-10-23 | ADR-0002 | Keep Flask; server-rendered UI; no database or AI service | accepted (follows existing spec §3.2/§6) | engineering |
| 2026-10-23 | ADR-0003 | Docker image on Render, CI-gated deploy | proposed | — |

### Document roles

- `intent.md` remains the product-purpose reference. Update it only when product intent changes, not merely to list implementation details.
- `spec.md` records requirements, decisions, and known constraints. Update it when requirements, formulas, policy decisions, provider choice, or scope change.
- `README.md` documents the shipped app and local operation. Keep it aligned with tested behavior.
- `CLAUDE.md` remains engineering context for future implementation and should link to this specification when work begins.
- Any change to formula definitions, recommendation semantics, external data handling, user-data retention, or provider integration requires corresponding tests and a spec update.
- `plan.md` sequences the work and tracks status; `docs/ai-sdlc.md` defines the build/verify/ship process; `docs/runbook.md` covers operations; `docs/adr/` records architecture decisions.

## 13. Requirement traceability

Maintained with `plan.md`. A requirement with no task is either deferred (P1/P2) or a gap to fix.

| Requirement | Plan task(s) | Primary verification |
|---|---|---|
| FR-01 | 2.1 | Page renders; form works without JS |
| FR-02 | 1.1, 1.2, 1.8 | Validation boundary tests; route tests |
| FR-03 | 1.5, 1.8, 2.2 | Provider fixture with multiple candidates → `AMBIGUOUS_MATCH` |
| FR-04 | 1.5, 1.7 | Provenance present on every retrieved field |
| FR-05 | 1.2, 2.1 | Bounds tests; inputs preserved on error |
| FR-06, FR-07 | 1.3, 2.3 | `golden_vectors.json` reproduced; debt service excluded from NOI |
| FR-08 | 1.3, 2.3 | Methodology text and units rendered |
| FR-09 | 1.4, 1.6, 1.7 | Missing data ⇒ `unavailable`; BD-01/BD-02 regression tests |
| FR-10 | 1.1, 1.5, 2.2 | Each error code mapped and shown |
| FR-11 | 1.10 | No verdict without user criteria |
| FR-12 | 2.1, 2.3 | Disclaimer visible in page and results |
| FR-13 | 2.5 | README matches tested behavior |
| FR-14 … FR-20 | 3.2 … 3.7 | Scheduled later |
| FR-21 | D5 | `test_healthz_is_ok_and_reports_version` |
| FR-22 | 3.1 (P0 if provider denied) | Manual-entry route tests |
| OPS-01 | D3, D7 | CI required on `main` |
| OPS-02 | D4 | Image builds in CI; container smoke |
| OPS-03, OPS-04 | D4, D8 | Render deploy gated on checks; smoke workflow |
| OPS-05 | D9 | Rollback rehearsal recorded |
| OPS-06 | D1 | `.env.example` lists all variables |
| OPS-07 | 1.9 | Log-content test |
| OPS-08 … OPS-11 | 3.8, 3.9 (Dependabot config already present) | Scheduled later |
| BD-01 … BD-09 | 1.4–1.10, 3.3 | One named regression test each |
| BD-10 | D6 | Scripts start app from `requirements.txt` |
| BD-11 | D1–D5 | Delivery foundation in place |
