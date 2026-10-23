# DealScope — Product Intent

## Product purpose

Help residential real-estate investors answer one first-pass question about a US address: **"Given the rent a home here can plausibly earn, what is the most I can pay and still have rent cover the mortgage, property tax and insurance — and leave a profit?"**

DealScope turns an address and a few optional financing assumptions into transparent maximum and target purchase prices, with the monthly math behind each. It is decision support, not a source of guaranteed property facts, a lender quote, tax or insurance advice, an appraisal, or a substitute for local due diligence.

## Intended users and job to be done

The primary user is an individual investor screening where to look. They want to quickly understand:

- What rent the local market appears to support.
- What purchase price makes the numbers work after paying PITI (principal and interest on the mortgage, property tax, insurance) and the other costs of owning a rental.
- How that price compares with what homes typically cost in the area.
- What assumptions, risks, and missing information could change the result.

The central workflow: **enter an address → see local rent and typical home value from public data → optionally adjust financing, cash-flow goal, and cost assumptions → read the price the home can support (PITI break-even, all-in break-even, target) → decide whether to investigate further.**

## Inputs: the address is the only thing the user provides

The only required input is a US address. DealScope must not ask users to type property facts (price, bedrooms, square footage) that the product could look up itself. The home is always evaluated **as one whole rental unit — never room by room**: one rent, one purchase price, one set of monthly costs. The goal is to identify the home's configuration (bedrooms, bathrooms, size) from a permitted source and compute rent and prices for that specific home. Until a permitted source is configured, the configuration is shown as "not identified" and the result describes a typical home in the ZIP, treated as a single unit. Financing and cost assumptions are optional, have visible defaults, and are tucked behind an "adjust assumptions" control.

## Data principle: free, public, permitted sources

Use free public data whose terms allow the use, and show attribution and "as of" dates:

- US Census Bureau Geocoder — address matching, ZIP, state, county.
- Zillow Research public indexes (observed rent index and home value index) by ZIP.
- State-average tax and insurance tables, labeled as low-confidence estimates until replaced by sourced data.

Do not scrape listing sites, use unofficial endpoints without a terms review, or bypass access controls or rate limits. County assessor records are valuable but there is no free national API; add county-level sources one at a time when an official free source with permitted use exists.

## Product direction

Implemented now:

- Address-only search with a clear, modern interface.
- ZIP-level typical rent and typical home value (public data) for one whole-home unit, and three prices: **PITI break-even**, **all-in break-even**, and **target price** (meets the user's monthly cash-flow goal).
- The monthly math at each price (PITI broken out; other costs; cash flow), plus cap rate and cash-on-cash at the target price.
- Visible assumptions, sources, and limitations; unknown values shown as unknown.

Planned (goals, not claims): identify the actual home's configuration and use its own rent and value estimate (needs a permitted source — Zillow listing pages and APIs are not available to us without a license, so a licensed or free-tier property-data API is the likely path), county-level property tax, comparable sales and price history, market snapshot, longer-term scenarios, user-defined buy-box criteria beyond cash flow, and sourced risk and opportunity summaries.

## Product principles

1. **Make assumptions visible.** Identify the source and nature of each input: public data, user-provided assumption, or model estimate.
2. **Prefer useful uncertainty to false precision.** Show missing data, ranges, and limitations rather than presenting defaults as verified facts.
3. **Explain recommendations.** A price is the output of stated assumptions and a formula the user can inspect; never an unexplained score or an instruction to buy.
4. **Support investigation, not financial guarantees.** Communicate that users must verify rents, taxes, insurance, financing, condition, and local rules.
5. **Keep the first-pass workflow approachable.** Ask only for the address; progressively reveal detail without hiding important costs.
6. **Fail visibly and safely.** An unavailable data source or invalid input must not produce a successful-looking analysis built on fabricated facts.
7. **Build incrementally.** Deliver cohesive, testable improvements that keep the implemented product and its documentation accurate.
8. **One home, one unit.** A house is evaluated as a single rental unit with one rent and one price, never room by room.
9. **Recommendations are calculations, not advice.** Prices are what the user's own criteria support. They are not appraisals, forecasts, or personalized investment advice, and the interface says so.

## Feature acceptance criteria

For a new or changed analysis feature, check that:

- Its user value and required inputs are clear (the address is still the only required input).
- Calculations and units are explicit and covered by focused tests, including round-trip checks of any solved price.
- The interface or API distinguishes public data, user assumptions, and estimates.
- Missing, malformed, and unavailable data produce understandable behavior.
- The output is consistent with related metrics and does not imply unsupported certainty.
- The data source's terms permit the use, and attribution and as-of dates are shown.
- README and this intent document reflect any material behavior change.

## Current known limitations

- Rent is a ZIP-level typical rent across all home sizes, not a quote for a specific property, and the home's configuration is not identified. The rent index lags the market by weeks and is smoothed.
- Property tax and insurance use state-average constants carried over from the prototype (unverified) unless the user enters rates. Actual bills vary by county, assessment, and property. DC and territories have no table and require entered rates.
- Home-level facts (bedrooms, bathrooms, size, condition, list price) and county assessor records are not retrieved; no permitted free national source is configured.
- Some ZIPs (PO box, institutional, tiny areas) have no rent data and return "insufficient data".
- Vacancy, management, and maintenance reserve are fixed default assumptions.
- Address matching uses the Census Geocoder, which can be slow or unavailable; the address is sent to it.
- Analyses are not stored (no database). The built-in rate limit is per process.

These limitations should be addressed explicitly when relevant to a feature; they should not be obscured by more confident UI language.
