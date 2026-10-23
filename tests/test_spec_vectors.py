"""Independent re-derivation of the spec's golden vectors.

This guards the *specification* against arithmetic mistakes: it recomputes every
expected value from first principles (spec.md §5.2). When dealscope.analysis exists
(plan.md task 1.3), add a test there that feeds the same JSON to the production code.
"""

import json
from pathlib import Path

import pytest

FIXTURE = Path(__file__).parent / "fixtures" / "golden_vectors.json"
VECTORS = json.loads(FIXTURE.read_text())["vectors"]


def derive(i):
    price = i["purchase_price"]
    down = price * i["down_payment_pct"] / 100
    loan = price - down
    n = i["loan_term_years"] * 12
    r = i["annual_interest_rate_pct"] / 100 / 12
    pi = loan / n if r == 0 else loan * r * (1 + r) ** n / ((1 + r) ** n - 1)
    rent = i["gross_monthly_rent"]
    tax = price * i["property_tax_rate_pct"] / 100 / 12
    ins = price * i["insurance_rate_pct"] / 100 / 12
    capex = price * i["capex_reserve_pct_of_price_per_year"] / 100 / 12
    vac = rent * i["vacancy_pct"] / 100
    mgmt = rent * i["management_pct"] / 100
    opex = tax + ins + i["hoa_monthly"] + capex + vac + mgmt
    noi = rent - opex
    cash_flow = noi - pi
    return {
        "down_payment": down,
        "loan_amount": loan,
        "monthly_principal_interest": pi,
        "monthly_property_tax": tax,
        "monthly_insurance": ins,
        "monthly_capex_reserve": capex,
        "monthly_vacancy": vac,
        "monthly_management": mgmt,
        "monthly_operating_expenses": opex,
        "monthly_noi": noi,
        "monthly_cash_flow": cash_flow,
        "cap_rate_pct": noi * 12 / price * 100,
        "cash_on_cash_pct": cash_flow * 12 / down * 100,
    }


@pytest.mark.parametrize("vector", VECTORS, ids=[v["name"] for v in VECTORS])
def test_expected_values_match_first_principles(vector):
    derived = derive(vector["inputs"])
    assert set(derived) == set(vector["expected"])
    for key, expected in vector["expected"].items():
        assert round(derived[key], 2) == pytest.approx(expected, abs=0.005), key


def test_noi_excludes_debt_service():
    v = VECTORS[0]
    d = derive(v["inputs"])
    assert d["monthly_noi"] - d["monthly_principal_interest"] == pytest.approx(
        d["monthly_cash_flow"]
    )
