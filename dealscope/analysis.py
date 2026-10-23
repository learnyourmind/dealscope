"""Deterministic financial analysis with provenance (spec §5.2, §6.2).

`compute_financials` and `max_purchase_price` are pure numeric code (golden vectors in
tests/fixtures/golden_vectors.json). `build_analysis` wraps them in the provenance model:
every value says whether it was retrieved, entered by the user, estimated, or is unavailable.
"""

import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from . import assumptions as A
from .errors import InsufficientData
from .provider import Location, ZipMarket
from .validation import AnalysisRequest

# ── Pure calculations ────────────────────────────────────────────────────────


def monthly_payment(loan: float, annual_rate_pct: float, years: int) -> float:
    """Level monthly principal and interest. Zero loan or zero rate are handled explicitly."""
    n = years * 12
    if loan <= 0:
        return 0.0
    r = annual_rate_pct / 100 / 12
    if r == 0:
        return loan / n
    growth = (1 + r) ** n
    return loan * r * growth / (growth - 1)


def compute_financials(
    *,
    purchase_price: float,
    down_payment_pct: float,
    annual_interest_rate_pct: float,
    loan_term_years: int,
    gross_monthly_rent: float,
    property_tax_rate_pct: float,
    insurance_rate_pct: float,
    hoa_monthly: float,
    vacancy_pct: float = A.VACANCY_PCT,
    management_pct: float = A.MANAGEMENT_PCT,
    capex_reserve_pct_of_price_per_year: float = A.CAPEX_PCT_OF_PRICE_PER_YEAR,
) -> Dict[str, float]:
    """All monthly figures unless the key says otherwise. NOI excludes debt service."""
    down = purchase_price * down_payment_pct / 100
    loan = purchase_price - down
    pi = monthly_payment(loan, annual_interest_rate_pct, loan_term_years)
    tax = purchase_price * property_tax_rate_pct / 100 / 12
    ins = purchase_price * insurance_rate_pct / 100 / 12
    capex = purchase_price * capex_reserve_pct_of_price_per_year / 100 / 12
    vacancy = gross_monthly_rent * vacancy_pct / 100
    mgmt = gross_monthly_rent * management_pct / 100
    opex = tax + ins + hoa_monthly + capex + vacancy + mgmt
    noi = gross_monthly_rent - opex
    cash_flow = noi - pi
    values = {
        "down_payment": down,
        "loan_amount": loan,
        "monthly_principal_interest": pi,
        "monthly_property_tax": tax,
        "monthly_insurance": ins,
        "monthly_capex_reserve": capex,
        "monthly_vacancy": vacancy,
        "monthly_management": mgmt,
        "monthly_operating_expenses": opex,
        "monthly_noi": noi,
        "monthly_cash_flow": cash_flow,
        "cap_rate_pct": noi * 12 / purchase_price * 100,
        "cash_on_cash_pct": cash_flow * 12 / down * 100,
    }
    return {key: round(value, 2) for key, value in values.items()}


def _rate_coefficient(
    down_payment_pct: float,
    annual_interest_rate_pct: float,
    loan_term_years: int,
    property_tax_rate_pct: float,
    insurance_rate_pct: float,
    capex_pct: float,
) -> float:
    """Monthly cost per $1 of purchase price: P&I on the loan + tax + insurance (+ CapEx)."""
    k = monthly_payment(1.0, annual_interest_rate_pct, loan_term_years)
    return (property_tax_rate_pct + insurance_rate_pct + capex_pct) / 1200 + (
        1 - down_payment_pct / 100
    ) * k


def max_purchase_price(
    *,
    gross_monthly_rent: float,
    down_payment_pct: float,
    annual_interest_rate_pct: float,
    loan_term_years: int,
    property_tax_rate_pct: float,
    insurance_rate_pct: float,
    hoa_monthly: float = 0.0,
    min_monthly_cash_flow: float = 0.0,
    include_operating_costs: bool = True,
    vacancy_pct: float = A.VACANCY_PCT,
    management_pct: float = A.MANAGEMENT_PCT,
    capex_reserve_pct_of_price_per_year: float = A.CAPEX_PCT_OF_PRICE_PER_YEAR,
) -> Optional[float]:
    """Highest purchase price whose monthly cash flow is at least `min_monthly_cash_flow`.

    Every cost except HOA scales linearly with price, so the answer is closed-form:
        cash_flow(P) = rent·(1 − vac − mgmt) − HOA − P·coefficient
    With `include_operating_costs=False` only mortgage P&I, tax, insurance (PITI) and HOA are
    deducted. Returns None when no positive price meets the target (rent too low).
    """
    income = gross_monthly_rent
    capex = 0.0
    if include_operating_costs:
        income *= 1 - (vacancy_pct + management_pct) / 100
        capex = capex_reserve_pct_of_price_per_year
    numerator = income - hoa_monthly - min_monthly_cash_flow
    coefficient = _rate_coefficient(
        down_payment_pct,
        annual_interest_rate_pct,
        loan_term_years,
        property_tax_rate_pct,
        insurance_rate_pct,
        capex,
    )
    if numerator <= 0 or coefficient <= 0:
        return None
    return numerator / coefficient


def floor_price(price: Optional[float], step: int = 1000) -> Optional[int]:
    """Round down so the stated price never overstates what the assumptions support."""
    if price is None or not math.isfinite(price):
        return None
    floored = int(math.floor(price / step) * step)
    return floored if floored >= step else None


def monthly_view(
    *,
    price: float,
    gross_monthly_rent: float,
    down_payment_pct: float,
    annual_interest_rate_pct: float,
    loan_term_years: int,
    property_tax_rate_pct: float,
    insurance_rate_pct: float,
    hoa_monthly: float,
    include_operating_costs: bool,
) -> Dict[str, float]:
    """Monthly picture at a given price: PITI first, then other costs, then cash flow."""
    pi = monthly_payment(
        price * (1 - down_payment_pct / 100), annual_interest_rate_pct, loan_term_years
    )
    tax = price * property_tax_rate_pct / 100 / 12
    ins = price * insurance_rate_pct / 100 / 12
    vacancy = management = capex = 0.0
    if include_operating_costs:
        vacancy = gross_monthly_rent * A.VACANCY_PCT / 100
        management = gross_monthly_rent * A.MANAGEMENT_PCT / 100
        capex = price * A.CAPEX_PCT_OF_PRICE_PER_YEAR / 100 / 12
    piti = pi + tax + ins
    other = hoa_monthly + vacancy + management + capex
    values = {
        "gross_rent": gross_monthly_rent,
        "principal_interest": pi,
        "property_tax": tax,
        "insurance": ins,
        "piti_total": piti,
        "hoa": hoa_monthly,
        "vacancy": vacancy,
        "management": management,
        "capex_reserve": capex,
        "other_costs_total": other,
        "cash_flow": gross_monthly_rent - piti - other,
        "down_payment": price * down_payment_pct / 100,
    }
    return {k: round(v, 2) for k, v in values.items()}


# ── Provenance model ─────────────────────────────────────────────────────────


def _fact(value: Any, unit: Optional[str], kind: str, **extra: Any) -> Dict[str, Any]:
    return {"value": value, "unit": unit, "kind": kind, **extra}


def _unavailable(reason: str, unit: Optional[str] = None) -> Dict[str, Any]:
    return {"kind": "unavailable", "reason": reason, "unit": unit}


SCENARIOS = (
    ("typical", "Typical home in this ZIP", None),
    ("1br", "1 bedroom", 1),
    ("2br", "2 bedrooms", 2),
    ("3br", "3 bedrooms", 3),
    ("4br", "4 bedrooms", 4),
)

PRICE_DEFS = (
    (
        "piti_breakeven",
        False,
        "zero",
        "Rent covers principal, interest, tax and insurance (PITI) exactly",
    ),
    (
        "allin_breakeven",
        True,
        "zero",
        "Cash flow is $0 after PITI, vacancy, management and maintenance reserve",
    ),
    (
        "target",
        True,
        "target",
        "Cash flow meets your monthly minimum after PITI and the other costs",
    ),
)


def build_analysis(req: AnalysisRequest, location: Location, market: ZipMarket) -> Dict[str, Any]:
    """Assumes the caller verified that `market.rent` exists."""
    state = location.state or market.state
    tax_rate = req.property_tax_rate_pct
    ins_rate = req.insurance_rate_pct
    tax_fact: Dict[str, Any]
    ins_fact: Dict[str, Any]
    if tax_rate is not None:
        tax_fact = _fact(tax_rate, "%/year", "user", source="You entered this")
    elif state in A.TAX_RATES:
        tax_rate = A.TAX_RATES[state]
        tax_fact = _fact(
            tax_rate,
            "%/year",
            "estimate",
            confidence="low",
            basis=f"{state} state-average effective property tax rate. {A.SOURCE}.",
        )
    else:
        tax_fact = _unavailable(
            "No state-average tax rate for this location; enter one under advanced assumptions.",
            "%/year",
        )
    if ins_rate is not None:
        ins_fact = _fact(ins_rate, "%/year", "user", source="You entered this")
    elif state in A.INS_RATES:
        ins_rate = A.INS_RATES[state]
        ins_fact = _fact(
            ins_rate,
            "%/year",
            "estimate",
            confidence="low",
            basis=f"{state} state-average homeowners insurance rate. {A.SOURCE}.",
        )
    else:
        ins_fact = _unavailable(
            "No state-average insurance rate for this location; "
            "enter one under advanced assumptions.",
            "%/year",
        )
    if tax_rate is None or ins_rate is None:
        raise InsufficientData(
            "We don't have state-average tax or insurance rates for this location. "
            "Enter both under Advanced assumptions to continue.",
            missing=["property_tax_rate_pct", "insurance_rate_pct"],
            needs_rates=True,
        )

    hoa_known = req.hoa_monthly is not None
    hoa = req.hoa_monthly or 0.0
    adj = req.rent_adjustment_pct
    typical_rent = market.rent * (1 + adj / 100)
    rent_source = f"{market.rent_source}, ZIP {market.zip}, {market.rent_as_of}"
    common = dict(
        down_payment_pct=req.down_payment_pct,
        annual_interest_rate_pct=req.annual_interest_rate_pct,
        loan_term_years=req.loan_term_years,
        property_tax_rate_pct=tax_rate,
        insurance_rate_pct=ins_rate,
    )

    scenarios: List[Dict[str, Any]] = []
    for key, label, beds in SCENARIOS:
        if beds is None:
            rent = typical_rent
            if adj == 0:
                rent_fact = _fact(
                    round(rent),
                    "USD/month",
                    "retrieved",
                    source=rent_source,
                    basis="Typical observed rent across home sizes in the ZIP; "
                    "not this property's rent.",
                )
            else:
                rent_fact = _fact(
                    round(rent),
                    "USD/month",
                    "estimate",
                    confidence="low",
                    basis=f"{rent_source} adjusted by your {adj:+g}%.",
                )
        else:
            rent = typical_rent * A.BEDROOM_RENT_FACTORS[beds]
            rent_fact = _fact(
                round(rent),
                "USD/month",
                "estimate",
                confidence="low",
                basis=f"{A.BEDROOM_FACTOR_BASIS} Base: {rent_source}.",
            )
        prices: Dict[str, Any] = {}
        views: Dict[str, Any] = {}
        for pkey, include_op, mode, note in PRICE_DEFS:
            raw = max_purchase_price(
                gross_monthly_rent=rent,
                hoa_monthly=hoa,
                min_monthly_cash_flow=req.min_monthly_cash_flow if mode == "target" else 0.0,
                include_operating_costs=include_op,
                **common,
            )
            price = floor_price(raw)
            if price is None:
                prices[pkey] = _unavailable(
                    "Rent is too low to meet this target at any purchase price.", "USD"
                )
                continue
            prices[pkey] = _fact(
                price,
                "USD",
                "estimate",
                confidence="low",
                basis=note + ". Rounded down to the nearest $1,000.",
            )
            views[pkey] = monthly_view(
                price=price,
                gross_monthly_rent=rent,
                hoa_monthly=hoa,
                include_operating_costs=include_op,
                **common,
            )
        target_price = prices["target"].get("value")
        extras: Dict[str, Any] = {}
        if target_price:
            fin = compute_financials(
                purchase_price=target_price,
                gross_monthly_rent=rent,
                hoa_monthly=hoa,
                **common,
            )
            extras = {
                "cap_rate_pct": fin["cap_rate_pct"],
                "cash_on_cash_pct": fin["cash_on_cash_pct"],
            }
            if market.home_value:
                extras["pct_of_zip_home_value"] = round(target_price / market.home_value * 100)
        scenarios.append(
            {
                "key": key,
                "label": label,
                "beds": beds,
                "rent": rent_fact,
                "prices": prices,
                "monthly_at_price": views,
                "at_target": extras,
            }
        )

    qualifier = (
        {}
        if hoa_known
        else {
            "qualified": True,
            "note": "HOA is unknown and counted as $0. A real HOA fee lowers every price shown.",
        }
    )
    assumptions = {
        "down_payment_pct": _fact(req.down_payment_pct, "%", "user", source="You entered this"),
        "annual_interest_rate_pct": _fact(
            req.annual_interest_rate_pct, "%", "user", source="You entered this"
        ),
        "loan_term_years": _fact(req.loan_term_years, "years", "user", source="You entered this"),
        "min_monthly_cash_flow": _fact(
            req.min_monthly_cash_flow, "USD/month", "user", source="You entered this"
        ),
        "rent_adjustment_pct": _fact(adj, "%", "user", source="You entered this"),
        "property_tax_rate_pct": tax_fact,
        "insurance_rate_pct": ins_fact,
        "hoa_monthly": (
            _fact(hoa, "USD/month", "user", source="You entered this")
            if hoa_known
            else _unavailable("Unknown; counted as $0 and flagged", "USD/month")
        ),
        "vacancy_pct": _fact(
            A.VACANCY_PCT,
            "%",
            "estimate",
            confidence="low",
            basis="Default assumption; not property-specific",
        ),
        "management_pct": _fact(
            A.MANAGEMENT_PCT,
            "%",
            "estimate",
            confidence="low",
            basis="Default assumption; not property-specific",
        ),
        "capex_reserve_pct": _fact(
            A.CAPEX_PCT_OF_PRICE_PER_YEAR,
            "% of price/year",
            "estimate",
            confidence="low",
            basis="Maintenance/CapEx reserve default; not property-specific",
        ),
    }

    market_json = {
        "zip": market.zip,
        "typical_rent": scenarios[0]["rent"],
        "typical_home_value": (
            _fact(
                round(market.home_value),
                "USD",
                "retrieved",
                source=f"{market.value_source}, ZIP {market.zip}, {market.value_as_of}",
                basis="Typical value of single-family homes and condos in the ZIP; "
                "not this property's value.",
            )
            if market.home_value
            else _unavailable("No home-value index for this ZIP", "USD")
        ),
    }

    limitations = [
        "For information only. This is not financial, tax, legal, insurance, appraisal, or lending "
        "advice, and it does not predict returns.",
        "Prices are the most you could pay for the stated cash flow under these assumptions. They "
        "are not an appraisal, a listing price, or a forecast of what the property will sell for.",
        "Rent is a ZIP-level typical rent across all home sizes, not a quote for a specific "
        "property. Bedroom rows scale it with a rough heuristic. Check local listings.",
        "Property tax and insurance use state averages unless you entered rates. Actual bills "
        "vary by county, assessment, and property.",
        "Vacancy, management, and maintenance reserve are default assumptions.",
        "Property facts such as bedroom count, size, condition, and county assessor records are "
        "not retrieved; no free national source is available for them.",
    ]
    if not hoa_known:
        limitations.append("HOA fees are unknown and counted as $0; results are qualified.")

    return {
        "location": {
            "address": _fact(
                location.address, None, "retrieved", source="US Census Bureau Geocoder"
            ),
            "zip": market.zip,
            "state": state,
            "county": location.county,
        },
        "market": market_json,
        "assumptions": assumptions,
        "scenarios": scenarios,
        "qualifier": qualifier,
        "limitations": limitations,
        "sources": [
            {
                "name": "US Census Bureau Geocoder",
                "url": "https://geocoding.geo.census.gov/",
                "used_for": "Address matching, ZIP, state, county",
            },
            {
                "name": market.rent_source,
                "url": "https://www.zillow.com/research/data/",
                "used_for": f"Typical rent ({market.rent_as_of})",
            },
            {
                "name": market.value_source,
                "url": "https://www.zillow.com/research/data/",
                "used_for": f"Typical home value ({market.value_as_of})",
            },
            {
                "name": "State-average tax and insurance tables (prototype constants, unverified)",
                "url": None,
                "used_for": "Property tax and insurance estimates",
            },
        ],
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
