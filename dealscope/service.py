"""Orchestration: validated request → geocode → area market data → analysis (spec §6)."""

import time
from typing import Any, Dict, Optional

from .analysis import build_analysis
from .errors import (
    AmbiguousMatch,
    InsufficientData,
    PropertyNotFound,
    ProviderAccessDenied,
    ProviderRateLimited,
    ProviderTimeout,
    ProviderUnavailable,
)
from .homes import HomeRecords
from .provider import Geocoder, MarketData
from .validation import parse_request


def _lookup_home(homes: Optional[HomeRecords], address: str, deadline: float):
    """Best-effort: a home lookup problem degrades the result, it never fails the analysis."""
    if homes is None or not homes.enabled:
        return None, None
    try:
        record = homes.lookup(address, deadline)
    except ProviderAccessDenied:
        return None, "the property-data source could not be used right now"
    except ProviderRateLimited:
        return None, "the property-data source is rate limited or its monthly quota is used up"
    except ProviderTimeout:
        return None, "the property-data source timed out"
    except ProviderUnavailable:
        return None, "the property-data source was unavailable"
    if record is None:
        return None, "no record was found for this address"
    return record, None


def run_analysis(
    payload: Any,
    geocoder: Geocoder,
    market: MarketData,
    homes: Optional[HomeRecords] = None,
    budget_s: float = 15.0,
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
    record, note = _lookup_home(homes, location.address, deadline)
    return {
        "success": True,
        "analysis": build_analysis(req, location, zip_market, home=record, home_note=note),
    }
