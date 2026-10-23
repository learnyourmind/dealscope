"""Orchestration: validated request → geocode → area market data → analysis (spec §6)."""

import time
from typing import Any, Dict

from .analysis import build_analysis
from .errors import AmbiguousMatch, InsufficientData, PropertyNotFound
from .provider import Geocoder, MarketData
from .validation import parse_request


def run_analysis(
    payload: Any, geocoder: Geocoder, market: MarketData, budget_s: float = 15.0
) -> Dict[str, Any]:
    req = parse_request(payload)
    deadline = time.monotonic() + budget_s

    locations = geocoder.geocode(req.address, deadline)
    if not locations:
        raise PropertyNotFound()
    if len(locations) > 1:
        raise AmbiguousMatch([loc.to_candidate() for loc in locations])
    location = locations[0]

    if not location.zip:
        raise InsufficientData(
            "The address matched, but no ZIP code was returned, so we can't look up local rents.",
            missing=["zip"],
        )
    zip_market = market.lookup(location.zip)
    if zip_market.rent is None:
        raise InsufficientData(
            f"We don't have rent data for ZIP {location.zip}. Try an address in a nearby ZIP.",
            missing=["rent"],
        )
    return {"success": True, "analysis": build_analysis(req, location, zip_market)}
