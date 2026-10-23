"""Translate the HTML form into the same payload the JSON API accepts."""

from typing import Any, Dict, Mapping

from .errors import InvalidRequest

_NUMERIC = {
    "down_payment_pct": ("assumptions", float),
    "annual_interest_rate_pct": ("assumptions", float),
    "loan_term_years": ("assumptions", int),
    "monthly_rent": ("assumptions", float),
    "purchase_price": ("property", float),
    "beds": ("property", int),
    "hoa_monthly": ("property", float),
}


def form_to_payload(form: Mapping[str, str]) -> Dict[str, Any]:
    """Blank optional fields are omitted so server defaults and 'unavailable' apply."""
    payload: Dict[str, Any] = {"address": form.get("address", "")}
    if form.get("candidate_id", "").strip():
        payload["candidate_id"] = form["candidate_id"].strip()
    sections: Dict[str, Dict[str, Any]] = {"assumptions": {}, "property": {}}
    for key, (section, cast) in _NUMERIC.items():
        raw = (form.get(key) or "").strip().replace(",", "")
        if not raw:
            continue
        try:
            sections[section][key] = cast(raw)
        except ValueError:
            field = key if section == "assumptions" else f"property.{key}"
            raise InvalidRequest(f"'{key}' must be a number.", field=field) from None
    state = (form.get("state") or "").strip()
    if state:
        sections["property"]["state"] = state
    payload["assumptions"] = sections["assumptions"]
    # A manual property needs at least price, beds, and state together; partial entry is
    # passed through so validation reports exactly which field is missing.
    if sections["property"]:
        payload["property"] = sections["property"]
    return payload
