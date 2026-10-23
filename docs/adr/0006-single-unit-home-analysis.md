# ADR-0006: Analyze one whole home as a single unit; home configuration needs a permitted source

- **Status:** Accepted for the single-unit behavior; the configuration source is pending the owner's choice
- **Date:** 2026-10-23
- **Amends:** [ADR-0005](./0005-address-only-free-public-data.md)

## Context
ADR-0005 shipped results for a typical home and for 1–4 bedrooms. The owner clarified that the product must not price or rent by room: a house is one rental unit, and its configuration should be identified from the listing data rather than guessed.

Zillow's listing pages and consumer APIs are not licensed for this use (scraping them is not permitted, and the official APIs are gated), so the configuration cannot come from Zillow listing data. Zillow Research's public ZIP indexes remain in use for area-level rent and value.

## Decision
- Remove the bedroom scenarios and the bedroom heuristic. The API returns exactly one `home` object.
- Add `home.configuration` (bedrooms, bathrooms, size) reported as `not_identified` with a reason until a permitted source exists. It is never guessed.
- Until then, the unit is a typical home in the ZIP, labeled as such everywhere.
- Track identification of the home's configuration as FR-23 / plan 4.9, blocked on the owner choosing a permitted source (for example a free-tier property-data API with its key held as a host secret).

## Consequences
- Fewer invented numbers: the heuristic factors are gone.
- Results are still area-level until 4.9 lands; the UI says so.
- Adding a source later should only fill `home.configuration` and replace the rent and value inputs; the price solver and UI stay as they are.

## Alternatives considered
Scraping Zillow (not permitted); asking the user for bedrooms (rejected by the owner's address-only direction); keeping bedroom rows (rejected: reads as renting by room).
