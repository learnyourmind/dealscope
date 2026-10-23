"""Translate the HTML form into the same payload the JSON API accepts."""

from typing import Any, Dict, Mapping

from .errors import InvalidRequest

_NUMERIC = {
    "down_payment_pct": float,
    "annual_interest_rate_pct": float,
    "loan_term_years": int,
    "min_monthly_cash_flow": float,
    "rent_adjustment_pct": float,
    "property_tax_rate_pct": float,
    "insurance_rate_pct": float,
    "hoa_monthly": float,
}


def form_to_payload(form: Mapping[str, str]) -> Dict[str, Any]:
    """Blank optional fields are omitted so server defaults and 'unknown' apply.

    A `pick` field (chosen from the ambiguous-match list) replaces the typed address.
    """
    address = (form.get("pick") or "").strip() or form.get("address", "")
    assumptions: Dict[str, Any] = {}
    for key, cast in _NUMERIC.items():
        raw = (form.get(key) or "").strip().replace(",", "").replace("$", "").replace("%", "")
        if not raw:
            continue
        try:
            assumptions[key] = cast(raw)
        except ValueError:
            raise InvalidRequest(f"'{key}' must be a number.", field=key) from None
    return {"address": address, "assumptions": assumptions}
