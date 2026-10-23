"""Deterministic financial analysis with provenance (spec §5.2, §6.2).

`compute_financials` is pure numeric code reproduced by tests/fixtures/golden_vectors.json.
`build_analysis` wraps it in the provenance model: every value says whether it was
retrieved, entered by the user, estimated, or is unavailable.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from . import assumptions as A
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


# ── Provenance model ─────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Fact:
    value: Any
    kind: str  # "retrieved" | "user"
    source: str
    retrieved_at: Optional[str] = None


@dataclass(frozen=True)
class PropertyFacts:
    address: Fact
    price: Optional[Fact] = None
    beds: Optional[Fact] = None
    state: Optional[Fact] = None
    sqft: Optional[Fact] = None
    hoa_monthly: Optional[Fact] = None
    property_type: Optional[Fact] = None


def _fact_json(
    fact: Optional[Fact], unit: Optional[str] = None, reason: str = "Not provided"
) -> Dict:
    if fact is None:
        return {"kind": "unavailable", "reason": reason, "unit": unit}
    out = {"value": fact.value, "kind": fact.kind, "source": fact.source, "unit": unit}
    if fact.retrieved_at:
        out["retrieved_at"] = fact.retrieved_at
    return out


def _estimate(value: Any, unit: str, basis: str, confidence: str = "low") -> Dict:
    return {
        "value": value,
        "unit": unit,
        "kind": "estimate",
        "basis": basis,
        "confidence": confidence,
    }


def _user(value: Any, unit: str) -> Dict:
    return {"value": value, "unit": unit, "kind": "user", "source": "You entered this"}


def _unavailable(reason: str, unit: Optional[str] = None) -> Dict:
    return {"kind": "unavailable", "reason": reason, "unit": unit}


def missing_required(facts: PropertyFacts) -> List[str]:
    return [name for name in ("price", "beds", "state") if getattr(facts, name) is None]


def build_analysis(req: AnalysisRequest, facts: PropertyFacts) -> Dict[str, Any]:
    """Assumes `missing_required(facts)` is empty."""
    price = float(facts.price.value)
    beds = int(facts.beds.value)
    state = str(facts.state.value)
    hoa_known = facts.hoa_monthly is not None
    hoa = float(facts.hoa_monthly.value) if hoa_known else 0.0

    tax_rate = A.TAX_RATES[state]
    ins_rate = A.INS_RATES[state]
    tax_basis = f"{state} state-average effective tax rate {tax_rate}% × price ÷ 12. {A.SOURCE}."
    ins_basis = f"{state} state-average insurance rate {ins_rate}% × price ÷ 12. {A.SOURCE}."

    # Rent: user value wins; otherwise a documented estimate; otherwise unavailable.
    rent_json: Dict
    if req.monthly_rent is not None:
        rent = float(req.monthly_rent)
        rent_json = _user(rent, "USD/month")
    else:
        est = A.estimate_rent(price, beds, state)
        if est is None:
            rent = None
            rent_json = _unavailable(
                f"No rent benchmark for {beds}-bedroom homes; enter your own rent estimate.",
                "USD/month",
            )
        else:
            rent = float(est[0])
            rent_json = _estimate(est[0], "USD/month", est[1])

    down_pct = req.down_payment_pct
    down = price * down_pct / 100
    loan = price - down
    pi = monthly_payment(loan, req.annual_interest_rate_pct, req.loan_term_years)

    tax = price * tax_rate / 100 / 12
    ins = price * ins_rate / 100 / 12
    capex = price * A.CAPEX_PCT_OF_PRICE_PER_YEAR / 100 / 12

    financing = {
        "down_payment": _estimate(round(down, 2), "USD", f"Price × {down_pct:g}% down payment"),
        "loan_amount": _estimate(round(loan, 2), "USD", "Price − down payment"),
        "monthly_principal_interest": _estimate(
            round(pi, 2),
            "USD/month",
            f"Level payment, {req.annual_interest_rate_pct:g}% nominal annual rate, "
            f"{req.loan_term_years}-year term. Not a lender quote.",
        ),
    }
    breakdown: Dict[str, Dict] = {
        "gross_rent": rent_json,
        "property_tax": _estimate(round(tax, 2), "USD/month", tax_basis),
        "insurance": _estimate(round(ins, 2), "USD/month", ins_basis),
        "hoa": _fact_json(
            facts.hoa_monthly,
            "USD/month",
            "HOA fee not available; treated as $0 in totals and flagged",
        ),
        "capex_reserve": _estimate(
            round(capex, 2),
            "USD/month",
            f"{A.CAPEX_PCT_OF_PRICE_PER_YEAR:g}% of price per year ÷ 12 "
            "(maintenance/CapEx reserve)",
        ),
    }

    metrics: Dict[str, Dict] = {}
    if rent is None:
        reason = "Rent is unavailable, so income-based metrics cannot be calculated."
        for key, unit in (
            ("vacancy", "USD/month"),
            ("management", "USD/month"),
            ("operating_expenses_total", "USD/month"),
        ):
            breakdown[key] = _unavailable(reason, unit)
        for key, unit in (
            ("monthly_noi", "USD/month"),
            ("monthly_cash_flow", "USD/month"),
            ("cap_rate_pct", "%"),
            ("cash_on_cash_pct", "%"),
        ):
            metrics[key] = _unavailable(reason, unit)
    else:
        calc = compute_financials(
            purchase_price=price,
            down_payment_pct=down_pct,
            annual_interest_rate_pct=req.annual_interest_rate_pct,
            loan_term_years=req.loan_term_years,
            gross_monthly_rent=rent,
            property_tax_rate_pct=tax_rate,
            insurance_rate_pct=ins_rate,
            hoa_monthly=hoa,
        )
        breakdown["vacancy"] = _estimate(
            calc["monthly_vacancy"], "USD/month", f"{A.VACANCY_PCT:g}% of gross monthly rent"
        )
        breakdown["management"] = _estimate(
            calc["monthly_management"], "USD/month", f"{A.MANAGEMENT_PCT:g}% of gross monthly rent"
        )
        breakdown["operating_expenses_total"] = _estimate(
            calc["monthly_operating_expenses"],
            "USD/month",
            "Tax + insurance + HOA + CapEx reserve + vacancy + management. Excludes debt service.",
        )
        qualifier = (
            {}
            if hoa_known
            else {
                "qualified": True,
                "missing_inputs": ["hoa_monthly"],
                "note": "HOA was unavailable and counted as $0; "
                "a real HOA fee would lower this result.",
            }
        )
        coc_note = (
            "Cash invested is the down payment only; closing costs and reserves are not included."
        )
        metrics["monthly_noi"] = {
            **_estimate(
                calc["monthly_noi"],
                "USD/month",
                "Income after vacancy − operating expenses; excludes principal and interest",
            ),
            **qualifier,
        }
        metrics["monthly_cash_flow"] = {
            **_estimate(calc["monthly_cash_flow"], "USD/month", "NOI − principal and interest"),
            **qualifier,
        }
        metrics["cap_rate_pct"] = {
            **_estimate(calc["cap_rate_pct"], "%", "Annual NOI ÷ purchase price × 100"),
            **qualifier,
        }
        metrics["cash_on_cash_pct"] = {
            **_estimate(
                calc["cash_on_cash_pct"],
                "%",
                "Annual pre-tax cash flow ÷ down payment × 100. " + coc_note,
            ),
            **qualifier,
        }

    assumptions_json = {
        "down_payment_pct": _user(down_pct, "%"),
        "annual_interest_rate_pct": _user(req.annual_interest_rate_pct, "%"),
        "loan_term_years": _user(req.loan_term_years, "years"),
        "vacancy_pct": _estimate(
            A.VACANCY_PCT, "%", "Default assumption; not property-specific", "low"
        ),
        "management_pct": _estimate(
            A.MANAGEMENT_PCT, "%", "Default assumption; not property-specific", "low"
        ),
        "property_tax_rate_pct": _estimate(tax_rate, "%/year", tax_basis),
        "insurance_rate_pct": _estimate(ins_rate, "%/year", ins_basis),
    }

    limitations = [
        "For information only. This is not financial, tax, legal, insurance, appraisal, "
        "or lending advice, "
        "and it does not predict returns.",
        "Property tax and insurance use state-average rates, not quotes for this property. "
        "Verify both locally.",
        "Rent, vacancy, management, and CapEx are model assumptions. "
        "Verify rents with local listings.",
        "Cash-on-cash return counts the down payment only; "
        "closing costs and reserves are excluded.",
        "No investment recommendation is made. Compare the figures with your own criteria.",
    ]
    if not hoa_known:
        limitations.append("HOA fees were unavailable and counted as $0; results are qualified.")
    if facts.price.kind == "user":
        limitations.append(
            "Price, bedrooms, and state were entered by you and have not been verified."
        )
    if rent is None:
        limitations.append(
            "Rent could not be estimated; enter your own monthly rent to calculate metrics."
        )

    return {
        "property": {
            "address": _fact_json(facts.address),
            "purchase_price": _fact_json(facts.price, "USD"),
            "beds": _fact_json(facts.beds, "bedrooms"),
            "state": _fact_json(facts.state),
            "sqft": _fact_json(facts.sqft, "sq ft"),
            "property_type": _fact_json(facts.property_type),
        },
        "assumptions": assumptions_json,
        "financing": financing,
        "breakdown": breakdown,
        "metrics": metrics,
        "limitations": limitations,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
