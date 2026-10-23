"""Request parsing and validation (spec FR-02, FR-05, §5.2 bounds).

Out-of-range values are rejected, never clamped. Messages name fields only.
"""

import math
import re
from dataclasses import dataclass
from typing import Any, Dict, Optional

from .assumptions import STATES
from .errors import InvalidRequest, OutOfRange

ADDRESS_MIN, ADDRESS_MAX = 5, 200
DOWN_PCT_MIN, DOWN_PCT_MAX = 5.0, 100.0
RATE_MIN, RATE_MAX = 0.0, 25.0
LOAN_TERMS = (15, 20, 30)
PRICE_MIN, PRICE_MAX = 10_000.0, 50_000_000.0
BEDS_MIN, BEDS_MAX = 0, 10
HOA_MIN, HOA_MAX = 0.0, 10_000.0
RENT_MIN, RENT_MAX = 100.0, 50_000.0

DEFAULT_DOWN_PCT = 20.0
DEFAULT_RATE = 7.0
DEFAULT_TERM = 30

_CANDIDATE_ID = re.compile(r"^\d{1,12}$")
_TOP_KEYS = {"address", "candidate_id", "assumptions", "property"}
_ASSUMPTION_KEYS = {
    "down_payment_pct",
    "annual_interest_rate_pct",
    "loan_term_years",
    "monthly_rent",
}
_PROPERTY_KEYS = {"purchase_price", "beds", "state", "hoa_monthly"}


@dataclass(frozen=True)
class ManualProperty:
    purchase_price: float
    beds: int
    state: str
    hoa_monthly: Optional[float] = None


@dataclass(frozen=True)
class AnalysisRequest:
    address: str
    candidate_id: Optional[str] = None
    down_payment_pct: float = DEFAULT_DOWN_PCT
    annual_interest_rate_pct: float = DEFAULT_RATE
    loan_term_years: int = DEFAULT_TERM
    monthly_rent: Optional[float] = None
    property: Optional[ManualProperty] = None


def _number(value: Any, field: str, lo: float, hi: float, integer: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise InvalidRequest(f"'{field}' must be a number.", field=field)
    if not math.isfinite(value):
        raise OutOfRange(f"'{field}' must be a finite number.", field=field)
    if integer and value != int(value):
        raise InvalidRequest(f"'{field}' must be a whole number.", field=field)
    if not lo <= value <= hi:
        raise OutOfRange(f"'{field}' must be between {lo:g} and {hi:g}.", field=field)
    return int(value) if integer else float(value)


def _object(value: Any, field: str, allowed: set) -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise InvalidRequest(f"'{field}' must be an object.", field=field)
    if set(value) - allowed:
        raise InvalidRequest(f"'{field}' contains an unsupported field.", field=field)
    return value


def parse_address(value: Any) -> str:
    if not isinstance(value, str):
        raise InvalidRequest("'address' is required.", field="address")
    text = value.strip()
    if any(ord(c) < 32 or ord(c) == 127 for c in text):
        raise InvalidRequest("'address' contains unsupported characters.", field="address")
    if not ADDRESS_MIN <= len(text) <= ADDRESS_MAX:
        raise OutOfRange(
            f"'address' must be {ADDRESS_MIN}-{ADDRESS_MAX} characters.", field="address"
        )
    return text


def _manual_property(raw: Any) -> ManualProperty:
    raw = _object(raw, "property", _PROPERTY_KEYS)
    for key in ("purchase_price", "beds", "state"):
        if key not in raw:
            raise InvalidRequest(f"'property.{key}' is required.", field=f"property.{key}")
    price = _number(raw["purchase_price"], "property.purchase_price", PRICE_MIN, PRICE_MAX)
    beds = _number(raw["beds"], "property.beds", BEDS_MIN, BEDS_MAX, integer=True)
    state = raw["state"]
    if not isinstance(state, str):
        raise InvalidRequest(
            "'property.state' must be a two-letter state code.", field="property.state"
        )
    state = state.strip().upper()
    if state not in STATES:
        raise OutOfRange(
            "'property.state' must be a supported US state code.", field="property.state"
        )
    hoa = raw.get("hoa_monthly")
    if hoa is not None:
        hoa = _number(hoa, "property.hoa_monthly", HOA_MIN, HOA_MAX)
    return ManualProperty(purchase_price=price, beds=beds, state=state, hoa_monthly=hoa)


def parse_request(payload: Any) -> AnalysisRequest:
    if not isinstance(payload, dict):
        raise InvalidRequest("The request body must be a JSON object.")
    if set(payload) - _TOP_KEYS:
        raise InvalidRequest("The request contains an unsupported field.")

    address = parse_address(payload.get("address"))

    candidate_id = payload.get("candidate_id")
    if candidate_id is not None:
        if not isinstance(candidate_id, str) or not _CANDIDATE_ID.match(candidate_id):
            raise InvalidRequest("'candidate_id' is not valid.", field="candidate_id")

    raw = _object(payload.get("assumptions", {}), "assumptions", _ASSUMPTION_KEYS)
    down = _number(
        raw.get("down_payment_pct", DEFAULT_DOWN_PCT),
        "down_payment_pct",
        DOWN_PCT_MIN,
        DOWN_PCT_MAX,
    )
    rate = _number(
        raw.get("annual_interest_rate_pct", DEFAULT_RATE),
        "annual_interest_rate_pct",
        RATE_MIN,
        RATE_MAX,
    )
    term = _number(
        raw.get("loan_term_years", DEFAULT_TERM), "loan_term_years", 1, 100, integer=True
    )
    if term not in LOAN_TERMS:
        raise OutOfRange("'loan_term_years' must be 15, 20, or 30.", field="loan_term_years")
    rent = raw.get("monthly_rent")
    if rent is not None:
        rent = _number(rent, "monthly_rent", RENT_MIN, RENT_MAX)

    manual = _manual_property(payload["property"]) if payload.get("property") is not None else None
    return AnalysisRequest(
        address=address,
        candidate_id=candidate_id,
        down_payment_pct=down,
        annual_interest_rate_pct=rate,
        loan_term_years=term,
        monthly_rent=rent,
        property=manual,
    )
