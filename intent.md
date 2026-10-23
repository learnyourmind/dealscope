# DealScope — Product Intent

## Product purpose

Help residential real-estate investors make a more informed first-pass decision about a US property by turning an address and a small set of investment assumptions into a transparent, understandable estimate of rental economics and purchase viability.

DealScope is decision support, not a source of guaranteed property facts, a lender quote, tax or insurance advice, or a substitute for local due diligence.

## Intended users and job to be done

The primary user is an individual investor evaluating a prospective residential rental property. They want to quickly understand:

- What the property and local market appear to look like.
- What rent and recurring ownership costs might be.
- Whether estimated operating performance fits their investment strategy.
- What assumptions, risks, and missing information could change the result.

The central workflow is: enter a property address, review the available property information, adjust financing or strategy assumptions, and use the resulting estimate to decide whether to investigate further.

## Product direction

The README describes the intended analysis experience as including:

- Property details and market context.
- An explainable rental estimate based on multiple methods.
- Estimated taxes, insurance, financing, and operating expenses.
- Cash flow, cap rate, cash-on-cash return, NOI, and gross rent multiplier.
- Comparable sales and price history when data is available.
- A buy-box recommendation with target, maximum, and walk-away pricing.
- Longer-term projections, investor scores, and clearly stated risks and opportunities.

These are product goals, not a claim that all features are currently implemented. The current code provides a basic Flask endpoint, Redfin lookup, rough regional rent/expense assumptions, a few financial outputs, and a simple verdict. The embedded page is a placeholder. Treat this gap as an opportunity for incremental feature work and keep product documentation aligned with shipped functionality.

## Product principles

1. **Make assumptions visible.** Identify the source and nature of each input: retrieved property data, user-provided assumptions, or model-based estimate.
2. **Prefer useful uncertainty to false precision.** Show missing data, estimate ranges, and limitations rather than presenting defaults as verified facts.
3. **Explain recommendations.** A verdict should be traceable to the figures and thresholds behind it; do not make an unexplained score the sole basis for a decision.
4. **Support investigation, not financial guarantees.** Clearly communicate that users must verify property condition, rents, taxes, insurance, financing, and local rules.
5. **Keep the first-pass workflow approachable.** Collect only the information needed for an initial estimate, and progressively reveal detail without hiding important costs.
6. **Fail visibly and safely.** An unavailable upstream data source or invalid input should not produce a successful-looking analysis based on fabricated property facts.
7. **Build incrementally.** Deliver cohesive, testable improvements that make the implemented product and its documentation more accurate.

## Feature acceptance criteria

For a new or changed analysis feature, check that:

- Its user value and required inputs are clear.
- Calculations and units are explicit and covered by focused tests.
- The interface or API distinguishes estimates from retrieved facts.
- Missing, malformed, and unavailable data produce understandable behavior.
- The output is consistent with related metrics and does not imply unsupported certainty.
- README and this intent document reflect any material behavior change.


## Current known limitations

- Automatic property lookup is off by default. The Redfin adapter depends on unofficial endpoints, is unverified against the live service, and needs a terms review before use; today the user enters price, bedrooms, and state.
- Rent, tax, and insurance rely on simplified state-level constants carried over from the prototype, not property-specific quotes or verified local research. They are labeled as low-confidence estimates.
- Cash-on-cash return counts the down payment only; closing costs and reserves are excluded and stated as such.
- No market snapshot, price history, comparable sales, multi-method rent estimate, projections, investor scores, risks/opportunities, or buy-box pricing yet; no recommendation is produced.
- Analyses are not stored (no database). The built-in rate limit is per process.

These limitations should be addressed explicitly when relevant to a feature; they should not be obscured by more confident UI language.
