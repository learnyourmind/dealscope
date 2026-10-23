import json
from pathlib import Path

import pytest

from dealscope.analysis import (
    build_analysis,
    compute_financials,
    floor_price,
    max_purchase_price,
    monthly_payment,
    monthly_view,
)
from dealscope.errors import InsufficientData
from dealscope.provider import Location, ZipMarket
from dealscope.validation import AnalysisRequest

VECTORS = json.loads((Path(__file__).parent / "fixtures" / "golden_vectors.json").read_text())[
    "vectors"
]
COMMON = dict(
    down_payment_pct=20,
    annual_interest_rate_pct=7.0,
    loan_term_years=30,
    property_tax_rate_pct=1.63,
    insurance_rate_pct=1.55,
)


@pytest.mark.parametrize("vector", VECTORS, ids=[v["name"] for v in VECTORS])
def test_compute_financials_reproduces_golden_vector(vector):
    result = compute_financials(**vector["inputs"])
    assert set(result) == set(vector["expected"])
    for key, expected in vector["expected"].items():
        assert result[key] == pytest.approx(expected, abs=0.005), key


def test_zero_interest_divides_loan_evenly():
    assert monthly_payment(360_000, 0, 30) == pytest.approx(1000.0)


def test_full_down_payment_has_zero_payment():
    assert monthly_payment(0, 7.0, 30) == 0.0


# ── price solver ────────────────────────────────────────────────────────────


@pytest.mark.parametrize("include_op", [True, False])
@pytest.mark.parametrize("target", [0.0, 100.0, 500.0])
@pytest.mark.parametrize("hoa", [0.0, 250.0])
def test_max_price_round_trips_to_the_cash_flow_target(include_op, target, hoa):
    price = max_purchase_price(
        gross_monthly_rent=3000,
        hoa_monthly=hoa,
        min_monthly_cash_flow=target,
        include_operating_costs=include_op,
        **COMMON,
    )
    view = monthly_view(
        price=price,
        gross_monthly_rent=3000,
        hoa_monthly=hoa,
        include_operating_costs=include_op,
        **COMMON,
    )
    assert view["cash_flow"] == pytest.approx(target, abs=0.05)


def test_all_in_view_matches_golden_calculation_at_the_solved_price():
    price = 250_000
    view = monthly_view(
        price=price, gross_monthly_rent=2800, hoa_monthly=0, include_operating_costs=True, **COMMON
    )
    full = compute_financials(
        purchase_price=price, gross_monthly_rent=2800, hoa_monthly=0, **COMMON
    )
    assert view["cash_flow"] == pytest.approx(full["monthly_cash_flow"], abs=0.02)
    assert view["principal_interest"] == pytest.approx(full["monthly_principal_interest"], abs=0.01)


def test_price_ordering_piti_ge_allin_ge_target():
    kw = dict(gross_monthly_rent=3000, hoa_monthly=0, **COMMON)
    piti = max_purchase_price(include_operating_costs=False, **kw)
    allin = max_purchase_price(include_operating_costs=True, **kw)
    target = max_purchase_price(include_operating_costs=True, min_monthly_cash_flow=200, **kw)
    assert piti > allin > target > 0


def test_price_moves_the_right_way():
    base = dict(gross_monthly_rent=3000, hoa_monthly=0, **COMMON)
    p = max_purchase_price(**base)
    assert max_purchase_price(**dict(base, gross_monthly_rent=3500)) > p
    assert max_purchase_price(**dict(base, annual_interest_rate_pct=9.0)) < p
    assert max_purchase_price(**dict(base, hoa_monthly=300)) < p
    assert max_purchase_price(**dict(base, property_tax_rate_pct=2.5)) < p


def test_rent_too_low_returns_none():
    assert max_purchase_price(gross_monthly_rent=100, hoa_monthly=400, **COMMON) is None
    assert max_purchase_price(gross_monthly_rent=1000, min_monthly_cash_flow=2000, **COMMON) is None


def test_zero_interest_and_full_down_payment_are_handled():
    kw = dict(gross_monthly_rent=3000, **COMMON)
    assert max_purchase_price(**dict(kw, annual_interest_rate_pct=0.0)) > max_purchase_price(**kw)
    assert max_purchase_price(**dict(kw, down_payment_pct=100)) > max_purchase_price(**kw)


@pytest.mark.parametrize(
    "value,expected",
    [(302_999.99, 302_000), (1_000, 1_000), (999.9, None), (None, None), (float("nan"), None)],
)
def test_floor_price_rounds_down_never_up(value, expected):
    assert floor_price(value) == expected


# ── provenance output ───────────────────────────────────────────────────────

LOC = Location("100 EXAMPLE ST, AUSTIN, TX, 78701", "78701", "TX", "Travis County")
MKT = ZipMarket(
    "78701",
    "TX",
    3177.0,
    650693.0,
    "2026-09",
    "2026-09",
    "Zillow Observed Rent Index (ZORI)",
    "Zillow Home Value Index (ZHVI)",
)


def analysis(req=None, location=LOC, market=MKT):
    return build_analysis(req or AnalysisRequest(address="100 Example St"), location, market)


def test_result_is_one_whole_home_unit_never_room_by_room():
    a = analysis()
    assert "scenarios" not in a and a["home"]["label"] == "Typical home in this ZIP"
    text = json.dumps(a).lower()
    assert "1br" not in text and "2 bedrooms" not in text and "bedroom factor" not in text
    assert any("whole unit" in t and "never rented room by room" in t for t in a["limitations"])


def test_home_configuration_is_reported_as_not_identified_not_guessed():
    cfg = analysis()["home"]["configuration"]
    assert cfg["status"] == "not_identified"
    for field in ("beds", "baths", "sqft"):
        assert cfg[field]["kind"] == "unavailable" and "value" not in cfg[field]


def test_typical_rent_is_public_data_with_source_and_home_value_context():
    a = analysis()
    rent = a["home"]["rent"]
    assert rent["kind"] == "retrieved" and "ZIP 78701" in rent["source"]
    assert "one whole unit" in rent["basis"]
    assert a["market"]["typical_rent"] == rent
    assert a["market"]["typical_home_value"]["kind"] == "retrieved"


def test_every_price_is_labelled_rounded_and_meets_the_goal():
    home = analysis(AnalysisRequest(address="x", min_monthly_cash_flow=250))["home"]
    for price in home["prices"].values():
        assert price["kind"] == "estimate" and price["value"] % 1000 == 0
    at = home["monthly_at_price"]["target"]
    assert at["cash_flow"] >= 250 - 0.01
    assert at["piti_total"] == pytest.approx(
        at["principal_interest"] + at["property_tax"] + at["insurance"], abs=0.02
    )


def test_target_is_below_all_in_which_is_below_piti_breakeven():
    p = {k: v["value"] for k, v in analysis()["home"]["prices"].items()}
    assert p["piti_breakeven"] > p["allin_breakeven"] >= p["target"]


def test_unknown_hoa_is_flagged_and_known_hoa_lowers_prices():
    unknown = analysis()
    known = analysis(AnalysisRequest(address="x", hoa_monthly=300))
    assert unknown["qualifier"]["qualified"] is True and "qualifier" and not known["qualifier"]
    assert unknown["assumptions"]["hoa_monthly"]["kind"] == "unavailable"
    assert known["home"]["prices"]["target"]["value"] < unknown["home"]["prices"]["target"]["value"]


def test_rent_adjustment_makes_typical_rent_an_estimate():
    a = analysis(AnalysisRequest(address="x", rent_adjustment_pct=10))
    rent = a["home"]["rent"]
    assert rent["kind"] == "estimate" and rent["value"] == round(3177 * 1.1)


def test_state_average_rates_are_low_confidence_and_overridable():
    a = analysis()
    tax = a["assumptions"]["property_tax_rate_pct"]
    assert tax["kind"] == "estimate" and tax["confidence"] == "low" and "TX" in tax["basis"]
    own = analysis(AnalysisRequest(address="x", property_tax_rate_pct=3.0, insurance_rate_pct=2.0))
    assert own["assumptions"]["property_tax_rate_pct"]["kind"] == "user"
    assert own["home"]["prices"]["target"]["value"] < a["home"]["prices"]["target"]["value"]


def test_location_without_state_average_requires_entered_rates():
    dc = Location("1600 PENNSYLVANIA AVE NW, WASHINGTON, DC, 20500", "20500", "DC", None)
    with pytest.raises(InsufficientData) as exc:
        analysis(
            location=dc,
            market=ZipMarket("20500", "DC", 3000.0, 700000.0, "2026-09", "2026-09", "R", "V"),
        )
    assert exc.value.details["needs_rates"] is True
    ok = analysis(
        AnalysisRequest(address="x", property_tax_rate_pct=0.6, insurance_rate_pct=0.5),
        location=dc,
        market=ZipMarket("20500", "DC", 3000.0, 700000.0, "2026-09", "2026-09", "R", "V"),
    )
    assert ok["home"]["prices"]["target"]["kind"] == "estimate"


def test_unreachable_target_is_unavailable_not_zero():
    a = analysis(AnalysisRequest(address="x", min_monthly_cash_flow=10000))
    target = a["home"]["prices"]["target"]
    assert target["kind"] == "unavailable" and "value" not in target
    assert a["home"]["monthly_at_price"].get("target") is None


def test_no_verdict_or_recommendation_words_in_output():
    text = json.dumps(analysis()).lower()
    assert '"verdict"' not in text and "recommendation" not in text.replace(
        "no investment recommendation", ""
    )
    assert "buy" not in text.split("limitations")[0]


def test_sources_and_limitations_are_present():
    a = analysis()
    assert any("Census" in s["name"] for s in a["sources"]) and any(
        "Zillow" in s["name"] for s in a["sources"]
    )
    assert any("not an appraisal" in t for t in a["limitations"])


def test_price_solver_reproduces_spec_price_vector():
    vec = json.loads((Path(__file__).parent / "fixtures" / "golden_vectors.json").read_text())[
        "price_vectors"
    ][0]
    i, exp = vec["inputs"], vec["expected"]
    kw = dict(
        gross_monthly_rent=i["gross_monthly_rent"],
        down_payment_pct=i["down_payment_pct"],
        annual_interest_rate_pct=i["annual_interest_rate_pct"],
        loan_term_years=i["loan_term_years"],
        property_tax_rate_pct=i["property_tax_rate_pct"],
        insurance_rate_pct=i["insurance_rate_pct"],
        hoa_monthly=i["hoa_monthly"],
    )
    assert (
        floor_price(max_purchase_price(include_operating_costs=False, **kw))
        == exp["piti_breakeven_price"]
    )
    assert (
        floor_price(max_purchase_price(include_operating_costs=True, **kw))
        == exp["allin_breakeven_price"]
    )
    target = floor_price(
        max_purchase_price(
            include_operating_costs=True, min_monthly_cash_flow=i["min_monthly_cash_flow"], **kw
        )
    )
    assert target == exp["target_price"]
    view = monthly_view(price=target, include_operating_costs=True, **kw)
    for key, expected in exp["monthly_at_target"].items():
        assert view[key] == pytest.approx(expected, abs=0.01), key
