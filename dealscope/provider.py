"""Data sources behind replaceable boundaries (spec FR-03, FR-04, FR-10, §5.5, §6.1).

* Geocoding: US Census Bureau Geocoder (free, no key, US government data).
* Area rent and home value: bundled snapshot of Zillow Research's public ZIP-level indexes,
  rebuilt by scripts/update_market_data.py (free, attribution shown in the app).

There is no free national API for county assessor records, and Redfin/Zillow listing pages are
not licensed for this use, so home-level facts (price, beds, baths, sqft) are not retrieved.
"""

import json
import time
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

from .errors import (
    InsufficientData,
    ProviderRateLimited,
    ProviderTimeout,
    ProviderUnavailable,
)

MAX_RESPONSE_BYTES = 2 * 1024 * 1024
MAX_CANDIDATES = 5
_USER_AGENT = "DealScope/0.2 (first-pass rental analysis)"
CENSUS_GEOCODER = "https://geocoding.geo.census.gov/geocoder/geographies/onelineaddress"
DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "zip_market.json"
GEOCODER_SOURCE = "US Census Bureau Geocoder"


@dataclass(frozen=True)
class Location:
    address: str  # standardized by the geocoder
    zip: Optional[str]
    state: Optional[str]
    county: Optional[str]

    def to_candidate(self) -> Dict[str, str]:
        return {"id": self.address, "display": self.address}


@dataclass(frozen=True)
class ZipMarket:
    zip: str
    state: Optional[str]
    rent: Optional[float]
    home_value: Optional[float]
    rent_as_of: str
    value_as_of: str
    rent_source: str
    value_source: str


def http_get_json(
    session: requests.Session,
    url: str,
    params: Dict[str, Any],
    timeouts: Tuple[float, float],
    deadline: Optional[float] = None,
    headers: Optional[Dict[str, str]] = None,
    not_found_ok: bool = False,
) -> Optional[Dict[str, Any]]:
    """GET JSON with bounded time and size; map every failure to a safe domain error.

    Returns None for HTTP 404 when `not_found_ok`. Never puts upstream text in an error.
    """
    connect, read = timeouts
    if deadline is not None:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise ProviderTimeout()
        read = min(read, remaining)
    try:
        resp = session.get(url, params=params, headers=headers, timeout=(connect, read))
    except requests.Timeout:
        raise ProviderTimeout() from None
    except requests.RequestException:
        raise ProviderUnavailable() from None
    status = resp.status_code
    if status == 404 and not_found_ok:
        return None
    if status in (403, 429):
        raise ProviderRateLimited()
    if status >= 400:
        raise ProviderUnavailable()
    body = resp.content or b""
    if len(body) > MAX_RESPONSE_BYTES:
        raise ProviderUnavailable()
    try:
        data = json.loads(body.decode("utf-8", errors="replace"))
    except ValueError:
        raise ProviderUnavailable() from None
    if not isinstance(data, (dict, list)):
        raise ProviderUnavailable()
    return data


class Geocoder:
    name = "base"
    enabled = True

    def geocode(self, address: str, deadline: Optional[float] = None) -> List[Location]:
        raise NotImplementedError


class DisabledGeocoder(Geocoder):
    name = "disabled"
    enabled = False

    def geocode(self, address, deadline=None):
        raise ProviderUnavailable("Address lookup is turned off in this deployment.")


class CensusGeocoder(Geocoder):
    name = "census"

    def __init__(
        self,
        connect_timeout: float = 3.0,
        read_timeout: float = 8.0,
        session: Optional[requests.Session] = None,
    ):
        self.timeouts = (connect_timeout, read_timeout)
        self.session = session or requests.Session()
        self.session.headers.update({"User-Agent": _USER_AGENT})

    def _get_json(self, params: Dict[str, Any], deadline: Optional[float]) -> Dict:
        data = http_get_json(self.session, CENSUS_GEOCODER, params, self.timeouts, deadline)
        if not isinstance(data, dict):
            raise ProviderUnavailable()
        return data

    def geocode(self, address: str, deadline: Optional[float] = None) -> List[Location]:
        data = self._get_json(
            {
                "address": address,
                "benchmark": "Public_AR_Current",
                "vintage": "Current_Current",
                "format": "json",
            },
            deadline,
        )
        result = data.get("result")
        matches = result.get("addressMatches") if isinstance(result, dict) else None
        if not isinstance(matches, list):
            raise ProviderUnavailable()
        out: List[Location] = []
        seen = set()
        for match in matches:
            if not isinstance(match, dict):
                continue
            text = match.get("matchedAddress")
            if not isinstance(text, str) or not text.strip() or text in seen:
                continue
            seen.add(text)
            comp = match.get("addressComponents")
            comp = comp if isinstance(comp, dict) else {}
            zip_code = comp.get("zip")
            state = comp.get("state")
            counties = (match.get("geographies") or {}).get("Counties")
            county = counties[0].get("NAME") if isinstance(counties, list) and counties else None
            out.append(
                Location(
                    address=text.strip(),
                    zip=zip_code if isinstance(zip_code, str) and zip_code.isdigit() else None,
                    state=state if isinstance(state, str) and len(state) == 2 else None,
                    county=county if isinstance(county, str) else None,
                )
            )
            if len(out) >= MAX_CANDIDATES:
                break
        return out


class MarketData:
    """ZIP-level rent and home value from the bundled snapshot."""

    def __init__(self, path: Path = DATA_FILE):
        self.path = path

    @lru_cache(maxsize=1)  # noqa: B019 - one shared snapshot per process is intended
    def _load(self) -> Dict[str, Any]:
        try:
            return json.loads(self.path.read_text())
        except (OSError, ValueError):
            raise ProviderUnavailable("Market data is unavailable.") from None

    def lookup(self, zip_code: str) -> ZipMarket:
        data = self._load()
        entry = data.get("zips", {}).get(zip_code)
        if not entry:
            raise InsufficientData(
                f"We don't have rent data for ZIP {zip_code}. It may be a PO box, unique "
                "(institutional) ZIP, or a very small area.",
                missing=["rent"],
            )
        rent, value, state = entry
        return ZipMarket(
            zip=zip_code,
            state=state,
            rent=float(rent) if rent else None,
            home_value=float(value) if value else None,
            rent_as_of=data["rent"]["as_of"],
            value_as_of=data["value"]["as_of"],
            rent_source=data["rent"]["name"],
            value_source=data["value"]["name"],
        )


def build_geocoder(name: str, connect_timeout: float, read_timeout: float) -> Geocoder:
    if name == "census":
        return CensusGeocoder(connect_timeout, read_timeout)
    return DisabledGeocoder()
