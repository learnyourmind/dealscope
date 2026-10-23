# DealScope — Product Requirements and Design Specification

**Status:** Draft for engineering planning  
**Source of truth:** `intent.md` for product intent; this document translates that intent into a proposed implementation for the current repository.  
**Product:** DealScope, a first-pass US residential rental-property analysis tool  
**Current implementation:** Flask application in `app.py`; current UI is a placeholder.

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

## 12. Documentation and change control

- `intent.md` remains the product-purpose reference. Update it only when product intent changes, not merely to list implementation details.
- `spec.md` records requirements, decisions, and known constraints. Update it when requirements, formulas, policy decisions, provider choice, or scope change.
- `README.md` documents the shipped app and local operation. Keep it aligned with tested behavior.
- `CLAUDE.md` remains engineering context for future implementation and should link to this specification when work begins.
- Any change to formula definitions, recommendation semantics, external data handling, user-data retention, or provider integration requires corresponding tests and a spec update.
