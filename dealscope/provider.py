"""Property-data provider boundary (spec FR-03, FR-04, FR-10, §5.5).

Calculations never see vendor JSON: adapters return normalized `PropertyFacts`.
The Redfin adapter targets an UNOFFICIAL endpoint whose use is pending terms review
(spec §7, plan P0-1), so the app ships with the provider disabled. Field paths below
are unverified against the live service and exercised only with synthetic fixtures.
"""

import json
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests

from .analysis import Fact, PropertyFacts
from .errors import (
    InsufficientData,
    ProviderRateLimited,
    ProviderTimeout,
    ProviderUnavailable,
)

MAX_RESPONSE_BYTES = 2 * 1024 * 1024
MAX_CANDIDATES = 5
_USER_AGENT = "DealScope/0.1 (+first-pass analysis tool)"


@dataclass(frozen=True)
class Candidate:
    id: str
    display: str

    def to_dict(self) -> Dict[str, str]:
        return {"id": self.id, "display": self.display}


class PropertyProvider:
    name = "base"
    enabled = True

    def search(self, address: str, deadline: Optional[float] = None) -> List[Candidate]:
        raise NotImplementedError

    def get_property(self, candidate: Candidate, deadline: Optional[float] = None) -> PropertyFacts:
        raise NotImplementedError


class DisabledProvider(PropertyProvider):
    name = "disabled"
    enabled = False

    def search(self, address, deadline=None):
        raise InsufficientData(
            "Automatic property lookup is turned off. Enter the price, bedrooms, and state.",
            missing=["price", "beds", "state"],
            manual_entry_required=True,
        )

    def get_property(self, candidate, deadline=None):  # pragma: no cover - never reached
        return self.search(candidate.display)


def _dig(obj: Any, *keys: str) -> Any:
    for key in keys:
        if not isinstance(obj, dict):
            return None
        obj = obj.get(key)
    return obj


def _positive_number(value: Any) -> Optional[float]:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value) if value > 0 else None


class RedfinProvider(PropertyProvider):
    name = "redfin"
    base = "https://www.redfin.com/stingray"

    def __init__(
        self,
        connect_timeout: float = 3.0,
        read_timeout: float = 8.0,
        session: Optional[requests.Session] = None,
    ):
        self.timeouts = (connect_timeout, read_timeout)
        self.session = session or requests.Session()
        self.session.headers.update({"User-Agent": _USER_AGENT})

    # ── transport ────────────────────────────────────────────────────────────
    def _get_json(self, path: str, params: Dict[str, Any], deadline: Optional[float]) -> Dict:
        connect, read = self.timeouts
        if deadline is not None:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise ProviderTimeout()
            read = min(read, remaining)
        try:
            resp = self.session.get(f"{self.base}{path}", params=params, timeout=(connect, read))
        except requests.Timeout:
            raise ProviderTimeout() from None
        except requests.RequestException:
            raise ProviderUnavailable() from None

        status = resp.status_code
        if status in (403, 429):
            raise ProviderRateLimited()
        if status >= 400:
            raise ProviderUnavailable()
        body = resp.content or b""
        if len(body) > MAX_RESPONSE_BYTES:
            raise ProviderUnavailable()
        text = body.decode("utf-8", errors="replace")
        if text.startswith("{}&&"):
            text = text[4:]
        try:
            data = json.loads(text)
        except ValueError:
            raise ProviderUnavailable() from None
        if not isinstance(data, dict):
            raise ProviderUnavailable()
        return data

    # ── search ───────────────────────────────────────────────────────────────
    @staticmethod
    def _property_id(row: Dict[str, Any]) -> Optional[str]:
        raw = str(row.get("id", ""))
        if ";" in raw:
            raw = raw.split(";")[0]
        match = re.search(r"/home/(\d{1,12})", str(row.get("url", "")))
        if match:
            return match.group(1)
        digits = re.search(r"(\d{1,12})$", raw)
        return digits.group(1) if digits and "_" in raw else None

    def search(self, address: str, deadline: Optional[float] = None) -> List[Candidate]:
        data = self._get_json("/do/location-autocomplete", {"location": address, "v": 2}, deadline)
        payload = data.get("payload")
        if not isinstance(payload, dict):
            raise ProviderUnavailable()
        rows: List[Dict[str, Any]] = []
        exact = payload.get("exactMatch")
        if isinstance(exact, dict):
            rows.append(exact)
        else:
            for section in payload.get("sections") or []:
                if isinstance(section, dict):
                    rows.extend(r for r in section.get("rows") or [] if isinstance(r, dict))
        seen, out = set(), []
        for row in rows:
            if "/home/" not in str(row.get("url", "")):
                continue  # not a specific property (city, neighborhood, ...)
            pid = self._property_id(row)
            if not pid or pid in seen:
                continue
            seen.add(pid)
            display = ", ".join(str(p).strip() for p in (row.get("name"), row.get("subName")) if p)
            out.append(Candidate(id=pid, display=display or "Unnamed property"))
            if len(out) >= MAX_CANDIDATES:
                break
        return out

    # ── details ──────────────────────────────────────────────────────────────
    def get_property(self, candidate: Candidate, deadline: Optional[float] = None) -> PropertyFacts:
        data = self._get_json(
            "/api/home/details/aboveTheFold",
            {"propertyId": candidate.id, "accessLevel": 3},
            deadline,
        )
        payload = data.get("payload")
        if not isinstance(payload, dict):
            raise ProviderUnavailable()
        stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")

        def fact(value: Any) -> Optional[Fact]:
            return None if value is None else Fact(value, "retrieved", self.name, stamp)

        price = _positive_number(_dig(payload, "listPrice", "value")) or _positive_number(
            _dig(payload, "priceInfo", "amount")
        )
        beds = _dig(payload, "beds")
        beds = (
            int(beds)
            if isinstance(beds, (int, float)) and not isinstance(beds, bool) and beds >= 0
            else None
        )
        state = _dig(payload, "addressSectionInfo", "state") or _dig(
            payload, "addressSectionInfo", "streetAddress", "state"
        )
        state = (
            state.strip().upper()
            if isinstance(state, str) and re.fullmatch(r"[A-Za-z]{2}", state.strip())
            else None
        )
        sqft = _positive_number(_dig(payload, "sqFt", "value"))
        hoa = _dig(payload, "hoa", "value")
        hoa = (
            float(hoa)
            if isinstance(hoa, (int, float)) and not isinstance(hoa, bool) and hoa >= 0
            else None
        )
        ptype = _dig(payload, "propertyType")

        return PropertyFacts(
            address=Fact(candidate.display, "retrieved", self.name, stamp),
            price=fact(price),
            beds=fact(beds),
            state=fact(state),
            sqft=fact(sqft),
            hoa_monthly=fact(hoa),
            property_type=fact(ptype if isinstance(ptype, str) and ptype else None),
        )


def build_provider(name: str, connect_timeout: float, read_timeout: float) -> PropertyProvider:
    if name == "redfin":
        return RedfinProvider(connect_timeout, read_timeout)
    return DisabledProvider()
