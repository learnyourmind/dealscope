import json
from pathlib import Path

import pytest

from dealscope.analysis import build_analysis, compute_financials, missing_required, monthly_payment
from dealscope.validation import AnalysisRequest, ManualProperty
from tests.conftest import retrieved_facts

VECTORS = json.loads((Path(__file__).parent / "fixtures" / "golden_vectors.json").read_text())[
    "vectors"
]


@pytest.mark.parametrize("vector", VECTORS, ids=[v["name"] for v in VECTORS])
def test_compute_financials_reproduces_golden_vector(vector):
    result = compute_financials(**vector["inputs"])
    assert set(result) == set(vector["expected"])
    for key, expected in vector["expected"].items():
        assert result[key] == pytest.approx(expected, abs=0.005), key


def test_noi_excludes_debt_service():
    r = compute_financials(**VECTORS[0]["inputs"])
    assert r["monthly_noi"] - r["monthly_principal_interest"] == pytest.approx(
        r["monthly_cash_flow"], abs=0.01
    )


def test_zero_interest_divides_loan_evenly():
    assert monthly_payment(360_000, 0, 30) == pytest.approx(1000.0)


def test_full_down_payment_has_zero_payment():
    assert monthly_payment(0, 7.0, 30) == 0.0


def test_negative_noi_is_reported_not_hidden():
    inputs = dict(VECTORS[0]["inputs"], gross_monthly_rent=500)
    r = compute_financials(**inputs)
    assert (
        r["monthly_noi"] < 0 and r["cap_rate_pct"] < 0 and r["monthly_cash_flow"] < r["monthly_noi"]
    )


def _request(**kw):
    return AnalysisRequest(address="100 Example St, Austin, TX", **kw)


def test_build_analysis_classifies_every_value():
    analysis = build_analysis(_request(), retrieved_facts())
    assert analysis["property"]["purchase_price"]["kind"] == "retrieved"
    assert analysis["breakdown"]["gross_rent"]["kind"] == "estimate"
    assert analysis["assumptions"]["down_payment_pct"]["kind"] == "user"
    assert analysis["metrics"]["monthly_cash_flow"]["kind"] == "estimate"
    assert "verdict" not in analysis and "recommendation" not in analysis


def test_user_rent_overrides_estimate():
    analysis = build_analysis(_request(monthly_rent=2800), retrieved_facts())
    assert analysis["breakdown"]["gross_rent"] == {
        "value": 2800.0,
        "unit": "USD/month",
        "kind": "user",
        "source": "You entered this",
    }


def test_missing_hoa_is_unavailable_and_qualifies_metrics():
    facts = retrieved_facts(hoa=None)
    analysis = build_analysis(_request(), facts)
    assert analysis["breakdown"]["hoa"]["kind"] == "unavailable"
    for key in ("monthly_noi", "monthly_cash_flow", "cap_rate_pct", "cash_on_cash_pct"):
        assert analysis["metrics"][key]["qualified"] is True
        assert analysis["metrics"][key]["missing_inputs"] == ["hoa_monthly"]


def test_known_hoa_does_not_qualify():
    analysis = build_analysis(_request(), retrieved_facts(hoa=0.0))
    assert "qualified" not in analysis["metrics"]["monthly_noi"]


def test_unsupported_bedroom_count_withholds_rent_dependent_metrics():
    analysis = build_analysis(_request(), retrieved_facts(beds=7))
    assert analysis["breakdown"]["gross_rent"]["kind"] == "unavailable"
    assert analysis["metrics"]["cap_rate_pct"]["kind"] == "unavailable"
    assert analysis["financing"]["monthly_principal_interest"]["value"] > 0  # still computable
    assert analysis["breakdown"]["property_tax"]["kind"] == "estimate"


def test_state_without_rent_table_discloses_national_fallback():
    analysis = build_analysis(_request(), retrieved_facts(state="WY"))
    assert "national fallback" in analysis["breakdown"]["gross_rent"]["basis"]


def test_estimates_state_their_basis_and_low_confidence():
    analysis = build_analysis(_request(), retrieved_facts())
    tax = analysis["breakdown"]["property_tax"]
    assert "TX" in tax["basis"] and "not independently verified" in tax["basis"]
    assert analysis["assumptions"]["property_tax_rate_pct"]["confidence"] == "low"


def test_missing_required_lists_absent_facts():
    assert missing_required(retrieved_facts(price=None, state=None)) == ["price", "state"]


def test_manual_property_marked_as_user_entered_in_limitations():
    from dealscope.service import _manual_facts

    req = _request(property=ManualProperty(300000, 3, "OH"))
    analysis = build_analysis(req, _manual_facts(req))
    assert analysis["property"]["purchase_price"]["kind"] == "user"
    assert any("entered by you" in text for text in analysis["limitations"])
