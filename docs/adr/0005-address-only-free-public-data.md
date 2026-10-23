# ADR-0005: Address-only input, price-solver output, free public data

- **Status:** Accepted (owner direction, 2026-10-23)
- **Supersedes:** the Redfin provider approach in spec v0.2 (P0-1) and manual entry (FR-22)

## Context
v0.2 asked users for price, bedrooms, and state (or planned to scrape Redfin's unofficial endpoints). The owner wants the address to be the only input, data from free public sources, and an answer to "what can I pay so that rent covers PITI and leaves a profit?".

Verified on 2026-10-23: the US Census Geocoder is free and keyless; the Census ACS API now requires a (free) key; Zillow Research publishes ZIP-level rent (ZORI) and home value (ZHVI) CSVs without a key. No free national API exists for county assessor records or for bedroom counts. Redfin and Zillow listing pages are not licensed for this use.

## Decision
- Input: address only; financing and cost assumptions are optional with defaults.
- Geocoding: Census Geocoder behind a `Geocoder` interface.
- Rent and home value: a bundled snapshot of Zillow Research ZIP indexes, rebuilt by `scripts/update_market_data.py`, so requests stay fast and independent of third-party availability.
- No property-level facts are asked for or retrieved. Answers are given for a typical home and 1–4 bedrooms; bedroom rent uses a disclosed heuristic.
- Output: closed-form maximum purchase prices (PITI break-even, all-in break-even, target for the user's cash-flow goal), with the monthly math. Prices are calculations from the user's criteria, not advice.
- The Redfin adapter and manual entry are removed.

## Consequences
- No property-specific accuracy: results describe the area, and the UI says so.
- The snapshot ages; a monthly refresh is required (plan task 4.4). Zillow terms need confirmation before wide or commercial use (spec §7 gate).
- Tax and insurance remain low-confidence state averages until a sourced county-level feed is added (needs a free Census key; plan 4.5).
- Vercel serves the data file with the function; no runtime dependency on Zillow.

## Alternatives considered
Census ACS for rents and taxes (needs a key the owner must obtain; planned as an enhancement); RentCast/ATTOM APIs (keyed, limited free tiers); scraping listing sites (not permitted).
