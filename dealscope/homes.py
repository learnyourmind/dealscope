"""Home-level records for the matched address (spec FR-23, ADR-0006).

Zillow listing pages and consumer APIs are not licensed for this use, so the home's own
configuration (bedrooms, bathrooms, size) and rent estimate come from a permitted property-data
API. RentCast's free Developer plan is the first adapter; its key is read from the environment
(`RENTCAST_API_KEY`, a host secret, never logged or committed).

One request per analysis: the long-term rent estimate returns the subject property's attributes
and the rent estimate together, which conserves the free plan's 50 requests per month. Lookup
failures never fail the analysis; the caller falls back to the ZIP-typical home and says why.

The endpoint paths and field names follow RentCast's published API reference
(developers.rentcast.io). They have not been exercised against the live service in this repo.
"""

import json
import logging
import math
import re
from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests

from .provider import http_get_json

log = logging.getLogger("dealscope")
_FIELD_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,40}$")
RENTCAST_RENT_URL = "https://api.rentcast.io/v1/avm/rent/long-term"
RENTCAST_NAME = "RentCast"
_USER_AGENT = "DealScope/0.3 (first-pass rental analysis)"
MULTI_UNIT_TYPES = {"Multi-Family", "Apartment"}


@dataclass(frozen=True)
class HomeRecord:
    address: Optional[str]
    rent: Optional[float]
    rent_low: Optional[float]
    rent_high: Optional[float]
    beds: Optional[int]
    baths: Optional[float]
    sqft: Optional[int]
    property_type: Optional[str]
    year_built: Optional[int]
    source: str = RENTCAST_NAME


class HomeRecords:
    name = "none"
    enabled = False

    def lookup(self, address: str, deadline: Optional[float] = None) -> Optional[HomeRecord]:
        return None


def _num(value: Any, minimum: float = 0.0, integer: bool = False) -> Optional[float]:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if not math.isfinite(value) or value < minimum:
        return None
    return int(value) if integer else float(value)


def _text(value: Any) -> Optional[str]:
    return value.strip() if isinstance(value, str) and value.strip() else None


class RentCastHomes(HomeRecords):
    name = "rentcast"
    enabled = True

    def __init__(
        self,
        api_key: str,
        connect_timeout: float = 3.0,
        read_timeout: float = 8.0,
        session: Optional[requests.Session] = None,
    ):
        self._api_key = api_key
        self.timeouts = (connect_timeout, read_timeout)
        self.session = session or requests.Session()
        self.session.headers.update({"User-Agent": _USER_AGENT})

    def __repr__(self) -> str:  # never expose the key
        return "RentCastHomes(key=***)"

    def lookup(self, address: str, deadline: Optional[float] = None) -> Optional[HomeRecord]:
        data = http_get_json(
            self.session,
            RENTCAST_RENT_URL,
            {"address": address},
            self.timeouts,
            deadline,
            headers={"X-Api-Key": self._api_key, "Accept": "application/json"},
            not_found_ok=True,
            source="rentcast",
            keyed=True,
        )
        if not isinstance(data, dict):
            return None
        subject = data.get("subjectProperty")
        subject: Dict[str, Any] = subject if isinstance(subject, dict) else {}
        rent = _num(data.get("rent"), minimum=1.0)
        record = HomeRecord(
            address=_text(subject.get("formattedAddress")),
            rent=rent,
            rent_low=_num(data.get("rentRangeLow"), minimum=1.0) if rent else None,
            rent_high=_num(data.get("rentRangeHigh"), minimum=1.0) if rent else None,
            beds=_num(subject.get("bedrooms"), integer=True),
            baths=_num(subject.get("bathrooms")),
            sqft=_num(subject.get("squareFootage"), minimum=1.0, integer=True),
            property_type=_text(subject.get("propertyType")),
            year_built=_num(subject.get("yearBuilt"), minimum=1600.0, integer=True),
        )
        has_configuration = record.beds is not None or bool(record.baths) or bool(record.sqft)
        # Field NAMES only (never values, address, or key) so a missing-details result can be
        # diagnosed from the logs without another paid lookup.
        log.info(
            json.dumps(
                {
                    "event": "home_record",
                    "source": "rentcast",
                    "has_rent": bool(record.rent),
                    "has_configuration": has_configuration,
                    "has_subject": bool(subject),
                    "top_fields": sorted(k for k in data if _FIELD_NAME.match(str(k)))[:20],
                    "subject_fields": sorted(k for k in subject if _FIELD_NAME.match(str(k)))[:30],
                }
            )
        )
        has_anything = record.rent or record.beds is not None or record.sqft
        return record if has_anything else None


def build_homes(api_key: str, connect_timeout: float, read_timeout: float) -> HomeRecords:
    if api_key.strip():
        return RentCastHomes(api_key.strip(), connect_timeout, read_timeout)
    return HomeRecords()
