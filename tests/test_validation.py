import pytest

from dealscope.errors import InvalidRequest, OutOfRange
from dealscope.validation import parse_request

ADDR = "100 Example St, Austin, TX"


def ok(**assumptions):
    return parse_request({"address": ADDR, "assumptions": assumptions})


def test_address_alone_is_a_valid_request_with_defaults():
    r = parse_request({"address": ADDR})
    assert (r.down_payment_pct, r.annual_interest_rate_pct, r.loan_term_years) == (20.0, 7.0, 30)
    assert r.min_monthly_cash_flow == 100.0 and r.rent_adjustment_pct == 0.0
    assert (
        r.property_tax_rate_pct is None and r.insurance_rate_pct is None and r.hoa_monthly is None
    )


@pytest.mark.parametrize("payload", [None, [], "x", 5])
def test_non_object_body_rejected(payload):
    with pytest.raises(InvalidRequest):
        parse_request(payload)


@pytest.mark.parametrize(
    "payload",
    [
        {"address": ADDR, "property": {"purchase_price": 300000}},  # manual property entry is gone
        {"address": ADDR, "candidate_id": "1"},
        {"address": ADDR, "assumptions": {"down_pct": 20}},
        {"address": ADDR, "assumptions": "x"},
    ],
)
def test_unknown_fields_rejected(payload):
    with pytest.raises(InvalidRequest):
        parse_request(payload)


@pytest.mark.parametrize("address", [None, 5, "", "    ", "abc", "x" * 201, "12 Main\nSt, TX"])
def test_bad_addresses_rejected(address):
    with pytest.raises((InvalidRequest, OutOfRange)):
        parse_request({"address": address})


@pytest.mark.parametrize(
    "field,good,bad",
    [
        ("down_payment_pct", (5, 100), (4.99, 100.01, -1)),
        ("annual_interest_rate_pct", (0, 25), (-0.01, 25.01)),
        ("min_monthly_cash_flow", (0, 10000), (-1, 10000.01)),
        ("rent_adjustment_pct", (-50, 100), (-50.01, 100.01)),
        ("property_tax_rate_pct", (0, 5), (-0.1, 5.1)),
        ("insurance_rate_pct", (0, 5), (-0.1, 5.1)),
        ("hoa_monthly", (0, 10000), (-1, 10000.01)),
    ],
)
def test_numeric_bounds_are_inclusive_and_rejected_not_clamped(field, good, bad):
    for value in good:
        assert ok(**{field: value}) is not None
    for value in bad:
        with pytest.raises(OutOfRange):
            ok(**{field: value})


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf"), 1e999])
def test_non_finite_numbers_rejected(value):
    with pytest.raises(OutOfRange):
        ok(annual_interest_rate_pct=value)


@pytest.mark.parametrize("value", [True, False, "7", [7], {"a": 1}])
def test_wrong_types_rejected(value):
    with pytest.raises(InvalidRequest):
        ok(annual_interest_rate_pct=value)


@pytest.mark.parametrize(
    "term,valid", [(15, True), (20, True), (30, True), (25, False), (0, False), (40, False)]
)
def test_loan_term_must_be_supported(term, valid):
    if valid:
        assert ok(loan_term_years=term).loan_term_years == term
    else:
        with pytest.raises(OutOfRange):
            ok(loan_term_years=term)


def test_fractional_term_rejected():
    with pytest.raises(InvalidRequest):
        ok(loan_term_years=30.5)


def test_error_messages_never_echo_user_input():
    with pytest.raises(InvalidRequest) as exc:
        parse_request({"address": ADDR, "assumptions": {"<script>": 1}})
    assert "<script>" not in exc.value.message
