"""Request parsing and validation (spec FR-02, FR-05, §5.2 bounds).

The only required input is an address. Everything else is an optional assumption.
Out-of-range values are rejected, never clamped. Messages name fields only.
"""

import math
from dataclasses import dataclass
from typing import Any, Dict, Optional

from .errors import InvalidRequest, OutOfRange

ADDRESS_MIN, ADDRESS_MAX = 5, 200
DOWN_PCT_MIN, DOWN_PCT_MAX = 5.0, 100.0
RATE_MIN, RATE_MAX = 0.0, 25.0
LOAN_TERMS = (15, 20, 30)
MIN_CF_MIN, MIN_CF_MAX = 0.0, 10_000.0
RENT_ADJ_MIN, RENT_ADJ_MAX = -50.0, 100.0
TAX_RATE_MIN, TAX_RATE_MAX = 0.0, 5.0
INS_RATE_MIN, INS_RATE_MAX = 0.0, 5.0
HOA_MIN, HOA_MAX = 0.0, 10_000.0

DEFAULT_DOWN_PCT = 20.0
DEFAULT_RATE = 7.0
DEFAULT_TERM = 30
DEFAULT_MIN_CASH_FLOW = 100.0

_TOP_KEYS = {"address", "assumptions"}
_ASSUMPTION_KEYS = {
    "down_payment_pct",
    "annual_interest_rate_pct",
    "loan_term_years",
    "min_monthly_cash_flow",
    "rent_adjustment_pct",
    "property_tax_rate_pct",
    "insurance_rate_pct",
    "hoa_monthly",
}


@dataclass(frozen=True)
class AnalysisRequest:
    address: str
    down_payment_pct: float = DEFAULT_DOWN_PCT
    annual_interest_rate_pct: float = DEFAULT_RATE
    loan_term_years: int = DEFAULT_TERM
    min_monthly_cash_flow: float = DEFAULT_MIN_CASH_FLOW
    rent_adjustment_pct: float = 0.0
    property_tax_rate_pct: Optional[float] = None  # None -> state-average estimate
    insurance_rate_pct: Optional[float] = None  # None -> state-average estimate
    hoa_monthly: Optional[float] = None  # None -> unknown, treated as $0 and flagged


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


def _optional(raw: Dict[str, Any], key: str, lo: float, hi: float) -> Optional[float]:
    value = raw.get(key)
    return None if value is None else _number(value, key, lo, hi)


def parse_request(payload: Any) -> AnalysisRequest:
    if not isinstance(payload, dict):
        raise InvalidRequest("The request body must be a JSON object.")
    if set(payload) - _TOP_KEYS:
        raise InvalidRequest("The request contains an unsupported field.")

    address = parse_address(payload.get("address"))

    raw = payload.get("assumptions", {})
    if not isinstance(raw, dict):
        raise InvalidRequest("'assumptions' must be an object.", field="assumptions")
    if set(raw) - _ASSUMPTION_KEYS:
        raise InvalidRequest("'assumptions' contains an unsupported field.", field="assumptions")

    term = _number(raw.get("loan_term_years", DEFAULT_TERM), "loan_term_years", 1, 100, True)
    if term not in LOAN_TERMS:
        raise OutOfRange("'loan_term_years' must be 15, 20, or 30.", field="loan_term_years")
    return AnalysisRequest(
        address=address,
        down_payment_pct=_number(
            raw.get("down_payment_pct", DEFAULT_DOWN_PCT),
            "down_payment_pct",
            DOWN_PCT_MIN,
            DOWN_PCT_MAX,
        ),
        annual_interest_rate_pct=_number(
            raw.get("annual_interest_rate_pct", DEFAULT_RATE),
            "annual_interest_rate_pct",
            RATE_MIN,
            RATE_MAX,
        ),
        loan_term_years=term,
        min_monthly_cash_flow=_number(
            raw.get("min_monthly_cash_flow", DEFAULT_MIN_CASH_FLOW),
            "min_monthly_cash_flow",
            MIN_CF_MIN,
            MIN_CF_MAX,
        ),
        rent_adjustment_pct=_number(
            raw.get("rent_adjustment_pct", 0.0), "rent_adjustment_pct", RENT_ADJ_MIN, RENT_ADJ_MAX
        ),
        property_tax_rate_pct=_optional(raw, "property_tax_rate_pct", TAX_RATE_MIN, TAX_RATE_MAX),
        insurance_rate_pct=_optional(raw, "insurance_rate_pct", INS_RATE_MIN, INS_RATE_MAX),
        hoa_monthly=_optional(raw, "hoa_monthly", HOA_MIN, HOA_MAX),
    )
