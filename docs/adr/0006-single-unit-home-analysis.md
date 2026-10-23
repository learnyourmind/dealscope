# ADR-0006: Analyze one whole home as a single unit; home configuration needs a permitted source

- **Status:** Accepted. The owner chose a free-tier property API (RentCast) for the home configuration; the key is still to be supplied
- **Date:** 2026-10-23
- **Amends:** [ADR-0005](./0005-address-only-free-public-data.md)

## Context
ADR-0005 shipped results for a typical home and for 1–4 bedrooms. The owner clarified that the product must not price or rent by room: a house is one rental unit, and its configuration should be identified from the listing data rather than guessed.

Zillow's listing pages and consumer APIs are not licensed for this use (scraping them is not permitted, and the official APIs are gated), so the configuration cannot come from Zillow listing data. Zillow Research's public ZIP indexes remain in use for area-level rent and value.

## Decision
- Remove the bedroom scenarios and the bedroom heuristic. The API returns exactly one `home` object.
- Add `home.configuration` (bedrooms, bathrooms, size, type, year built). It is `identified` from a permitted source and `not_identified` with a reason otherwise. It is never guessed.
- Source: RentCast's long-term rent estimate, which returns the subject property's attributes and the rent estimate in a single request (conserving the free plan's 50 requests/month). The adapter is enabled only when `RENTCAST_API_KEY` is set (host secret).
- Any lookup failure, quota exhaustion, or missing record degrades to the ZIP-typical home with the reason shown; it never fails the analysis.
- Until then, the unit is a typical home in the ZIP, labeled as such everywhere.
- Until a key exists, the unit is a typical home in the ZIP, labeled as such.

## Consequences
- Fewer invented numbers: the heuristic factors are gone.
- Results are still area-level until 4.9 lands; the UI says so.
- The address is also sent to RentCast when enabled; the UI discloses it.
- The free plan is small (50 requests/month) and a public site can exhaust it; overage on that plan is $0.20 per request unless capped. The owner must cap billing in the RentCast account; the app's per-instance rate limit is not a quota guard.
- RentCast's terms for public display and caching must be read before production use (release gate in spec §7).
- Endpoint and field names follow RentCast's published reference and are not yet exercised live.

## Alternatives considered
Scraping Zillow (not permitted); asking the user for bedrooms (rejected by the owner's address-only direction); keeping bedroom rows (rejected: reads as renting by room).
