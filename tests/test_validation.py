import pytest

from dealscope.errors import InvalidRequest, OutOfRange
from dealscope.validation import parse_request

ADDR = "100 Example St, Austin, TX"


def ok(**extra):
    return parse_request({"address": ADDR, **extra})


def test_defaults_applied():
    r = ok()
    assert (r.down_payment_pct, r.annual_interest_rate_pct, r.loan_term_years) == (20.0, 7.0, 30)


@pytest.mark.parametrize("payload", [None, [], "x", 5])
def test_non_object_body_rejected(payload):
    with pytest.raises(InvalidRequest):
        parse_request(payload)


def test_unknown_top_level_and_nested_keys_rejected():
    with pytest.raises(InvalidRequest):
        ok(strategy="flip")
    with pytest.raises(InvalidRequest):
        ok(assumptions={"down_pct": 20})


@pytest.mark.parametrize("address", [None, 5, "", "    ", "abc", "x" * 201, "12 Main\nSt, TX"])
def test_bad_addresses_rejected(address):
    with pytest.raises((InvalidRequest, OutOfRange)):
        parse_request({"address": address})


@pytest.mark.parametrize(
    "field,good,bad",
    [
        ("down_payment_pct", (5, 100), (4.99, 100.01, -1)),
        ("annual_interest_rate_pct", (0, 25), (-0.01, 25.01)),
        ("monthly_rent", (100, 50000), (99.99, 50000.01)),
    ],
)
def test_numeric_bounds_are_inclusive_and_rejected_not_clamped(field, good, bad):
    for value in good:
        assert ok(assumptions={field: value}) is not None
    for value in bad:
        with pytest.raises(OutOfRange):
            ok(assumptions={field: value})


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf"), 1e999])
def test_non_finite_numbers_rejected(value):
    with pytest.raises(OutOfRange):
        ok(assumptions={"annual_interest_rate_pct": value})


@pytest.mark.parametrize("value", [True, False, "7", [7], {"a": 1}])
def test_wrong_types_rejected(value):
    with pytest.raises(InvalidRequest):
        ok(assumptions={"annual_interest_rate_pct": value})


@pytest.mark.parametrize(
    "term,valid", [(15, True), (20, True), (30, True), (25, False), (0, False), (40, False)]
)
def test_loan_term_must_be_supported(term, valid):
    if valid:
        assert ok(assumptions={"loan_term_years": term}).loan_term_years == term
    else:
        with pytest.raises(OutOfRange):
            ok(assumptions={"loan_term_years": term})


def test_fractional_term_rejected():
    with pytest.raises(InvalidRequest):
        ok(assumptions={"loan_term_years": 30.5})


@pytest.mark.parametrize("cid", ["123", "1" * 12])
def test_candidate_id_digits_only_accepted(cid):
    assert ok(candidate_id=cid).candidate_id == cid


@pytest.mark.parametrize("cid", ["", "12a", "../etc", "1" * 13, 123, "1;2"])
def test_candidate_id_rejects_anything_else(cid):
    with pytest.raises(InvalidRequest):
        ok(candidate_id=cid)


def test_manual_property_parsed_and_state_normalized():
    r = ok(property={"purchase_price": 300000, "beds": 3, "state": " oh ", "hoa_monthly": 50})
    assert (r.property.state, r.property.beds, r.property.hoa_monthly) == ("OH", 3, 50.0)


@pytest.mark.parametrize(
    "prop,exc",
    [
        ({"beds": 3, "state": "TX"}, InvalidRequest),
        ({"purchase_price": 9999, "beds": 3, "state": "TX"}, OutOfRange),
        ({"purchase_price": 300000, "beds": 3, "state": "ZZ"}, OutOfRange),
        ({"purchase_price": 300000, "beds": 3.5, "state": "TX"}, InvalidRequest),
        ({"purchase_price": 300000, "beds": 11, "state": "TX"}, OutOfRange),
        ({"purchase_price": 300000, "beds": 3, "state": "TX", "hoa_monthly": -1}, OutOfRange),
        ({"purchase_price": 300000, "beds": 3, "state": "TX", "url": "http://x"}, InvalidRequest),
    ],
)
def test_manual_property_rejections(prop, exc):
    with pytest.raises(exc):
        ok(property=prop)


def test_error_messages_never_echo_user_input():
    with pytest.raises(OutOfRange) as exc:
        ok(property={"purchase_price": 300000, "beds": 3, "state": "<script>"})
    assert "<script>" not in exc.value.message
