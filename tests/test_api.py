import json
import logging

import pytest

from dealscope.errors import ProviderRateLimited, ProviderTimeout, ProviderUnavailable
from tests.conftest import FakeGeocoder, FakeHomes, home_record, loc, make_client

BODY = {"address": "100 Example St, Austin, TX"}


def post(client, body, **kw):
    return client.post("/analyze", json=body, **kw)


def test_address_only_request_returns_one_whole_home_result(client):
    resp = post(client, BODY)
    assert resp.status_code == 200
    a = resp.get_json()["analysis"]
    assert a["location"]["zip"] == "78701" and a["market"]["typical_rent"]["value"] == 3177
    assert "scenarios" not in a and a["home"]["configuration"]["status"] == "not_identified"
    prices = a["home"]["prices"]
    assert (
        prices["piti_breakeven"]["value"]
        > prices["allin_breakeven"]["value"]
        >= prices["target"]["value"]
        > 0
    )


def test_assumptions_change_the_answer(client):
    base = post(client, BODY).get_json()["analysis"]["home"]["prices"]["target"]["value"]
    high_rate = post(client, dict(BODY, assumptions={"annual_interest_rate_pct": 9.5}))
    assert high_rate.get_json()["analysis"]["home"]["prices"]["target"]["value"] < base


def test_ambiguous_matches_require_selection(market):
    geo = FakeGeocoder([loc("1 A ST, AUSTIN, TX, 78701"), loc("1 A ST, AUSTIN, TX, 78702")])
    resp = post(make_client(market, geo), BODY)
    err = resp.get_json()["error"]
    assert resp.status_code == 422 and err["code"] == "AMBIGUOUS_MATCH"
    assert [c["id"] for c in err["candidates"]] == [
        "1 A ST, AUSTIN, TX, 78701",
        "1 A ST, AUSTIN, TX, 78702",
    ]


def test_address_not_found(market):
    resp = post(make_client(market, FakeGeocoder([])), BODY)
    assert resp.status_code == 404 and resp.get_json()["error"]["code"] == "PROPERTY_NOT_FOUND"


@pytest.mark.parametrize(
    "location,missing",
    [
        (loc(zip=None), "zip"),
        (loc(zip="59001", state="MT"), "rent"),  # ZIP known but no rent index value
        (loc(zip="00000"), "rent"),  # ZIP not in snapshot
    ],
)
def test_missing_area_data_is_insufficient_data_not_a_fabricated_rent(market, location, missing):
    resp = post(make_client(market, FakeGeocoder([location])), BODY)
    err = resp.get_json()["error"]
    assert (
        resp.status_code == 422 and err["code"] == "INSUFFICIENT_DATA" and missing in err["missing"]
    )


def test_state_without_average_rates_asks_for_them(market):
    geo = FakeGeocoder(
        [loc("1600 PENNSYLVANIA AVE NW, WASHINGTON, DC, 20500", zip="20500", state="DC")]
    )
    err = post(make_client(market, geo), BODY).get_json()["error"]
    assert err["code"] == "INSUFFICIENT_DATA" and err["needs_rates"] is True
    ok = post(
        make_client(market, geo),
        dict(BODY, assumptions={"property_tax_rate_pct": 0.6, "insurance_rate_pct": 0.5}),
    )
    assert ok.status_code == 200


@pytest.mark.parametrize(
    "error,status,code",
    [
        (ProviderTimeout(), 504, "PROVIDER_TIMEOUT"),
        (ProviderUnavailable(), 502, "PROVIDER_UNAVAILABLE"),
    ],
)
def test_provider_failures_map_to_status_and_retryable(market, error, status, code):
    resp = post(make_client(market, FakeGeocoder(error=error)), BODY)
    body = resp.get_json()["error"]
    assert resp.status_code == status and body["code"] == code and body["retryable"] is True


@pytest.mark.parametrize(
    "body,status,code",
    [
        ({}, 400, "INVALID_REQUEST"),
        ({"address": "100 Example St", "bogus": 1}, 400, "INVALID_REQUEST"),
        ({"address": "100 Example St", "property": {"purchase_price": 1}}, 400, "INVALID_REQUEST"),
        (
            {"address": "100 Example St", "assumptions": {"annual_interest_rate_pct": 99}},
            400,
            "OUT_OF_RANGE",
        ),
        (
            {"address": "100 Example St", "assumptions": {"annual_interest_rate_pct": "7"}},
            400,
            "INVALID_REQUEST",
        ),
    ],
)
def test_invalid_input_codes(client, body, status, code):
    resp = post(client, body)
    assert resp.status_code == status and resp.get_json()["error"]["code"] == code


def test_nan_literal_in_json_is_rejected(client):
    raw = '{"address": "100 Example St", "assumptions": {"annual_interest_rate_pct": NaN}}'
    resp = client.post("/analyze", data=raw, content_type="application/json")
    assert resp.status_code == 400 and resp.get_json()["error"]["code"] == "OUT_OF_RANGE"


def test_non_json_content_type_rejected(client):
    resp = client.post("/analyze", data="address=x", content_type="text/plain")
    assert resp.status_code == 400 and resp.get_json()["error"]["code"] == "INVALID_REQUEST"


def test_malformed_json_rejected(client):
    resp = client.post("/analyze", data="{not json", content_type="application/json")
    assert resp.status_code == 400 and resp.get_json()["success"] is False


def test_oversized_body_rejected(client):
    resp = client.post("/analyze", data=b"x" * 9000, content_type="application/json")
    assert resp.status_code == 413 and resp.get_json()["success"] is False


def test_unexpected_exception_never_leaks_details(market):
    class Boom(FakeGeocoder):
        def geocode(self, address, deadline=None):
            raise RuntimeError("secret-token-123 /etc/passwd")

    resp = post(make_client(market, Boom()), BODY)
    text = resp.get_data(as_text=True)
    assert resp.status_code == 500 and "secret" not in text and "passwd" not in text
    body = resp.get_json()["error"]
    assert body["code"] == "INTERNAL_ERROR" and body["request_id"]


def test_unknown_route_and_method_use_envelope(client):
    assert client.get("/nope").get_json()["error"]["code"] == "NOT_FOUND"
    resp = client.get("/analyze")
    assert resp.status_code == 405 and resp.get_json()["error"]["code"] == "METHOD_NOT_ALLOWED"


def test_request_id_header_is_generated_and_echoed(client):
    assert client.get("/healthz").headers["X-Request-ID"]
    assert (
        client.get("/healthz", headers={"X-Request-ID": "abc-123"}).headers["X-Request-ID"]
        == "abc-123"
    )
    bad = client.get("/healthz", headers={"X-Request-ID": "bad id <x>"}).headers["X-Request-ID"]
    assert bad != "bad id <x>" and len(bad) == 32


def test_cors_off_by_default(client):
    resp = client.post("/analyze", json=BODY, headers={"Origin": "https://evil.example"})
    assert "Access-Control-Allow-Origin" not in resp.headers


def test_cors_only_for_configured_origin(market):
    client = make_client(market, cors_origins=("https://app.example",))
    ok = client.post("/analyze", json=BODY, headers={"Origin": "https://app.example"})
    other = client.post("/analyze", json=BODY, headers={"Origin": "https://evil.example"})
    assert ok.headers.get("Access-Control-Allow-Origin") == "https://app.example"
    assert "Access-Control-Allow-Origin" not in other.headers


def test_rate_limit_returns_429(market):
    client = make_client(market, rate_limit="2/minute")
    codes = [post(client, BODY).status_code for _ in range(3)]
    assert codes == [200, 200, 429]
    assert post(client, BODY).get_json()["error"]["code"] == "RATE_LIMITED"
    assert client.get("/healthz").status_code == 200


def test_logs_exclude_address_and_body(client, caplog):
    with caplog.at_level(logging.INFO, logger="dealscope"):
        post(client, {"address": "77 Secret Lane, Nowhere, ZZ"})
        post(
            client,
            {"address": "77 Secret Lane, Nowhere, ZZ", "assumptions": {"down_payment_pct": 1}},
        )
    text = "\n".join(r.getMessage() for r in caplog.records)
    assert "Secret Lane" not in text and "Example St" not in text
    records = [json.loads(r.getMessage()) for r in caplog.records]
    assert {"request_id", "route", "latency_ms", "error_code", "status"} <= set(records[0])
    assert records[1]["error_code"] == "OUT_OF_RANGE"


# ── identified home ───────────────────────────────────────────────────────────────


def test_identified_home_is_used_and_looked_up_once_with_the_matched_address(market):
    homes = FakeHomes(home_record())
    client = make_client(market, homes=homes)
    resp = post(client, BODY)
    h = resp.get_json()["analysis"]["home"]
    assert resp.status_code == 200 and h["label"] == "This home"
    assert h["configuration"]["status"] == "identified" and h["configuration"]["beds"]["value"] == 3
    assert homes.calls == ["100 EXAMPLE ST, AUSTIN, TX, 78701"]  # one request, standardized address


@pytest.mark.parametrize(
    "error,words",
    [
        (ProviderRateLimited(), "quota"),
        (ProviderTimeout(), "timed out"),
        (ProviderUnavailable(), "unavailable"),
    ],
)
def test_home_lookup_failure_degrades_to_the_zip_typical_home_not_an_error(market, error, words):
    resp = post(make_client(market, homes=FakeHomes(error=error)), BODY)
    a = resp.get_json()["analysis"]
    assert resp.status_code == 200 and a["home"]["label"] == "Typical home in this ZIP"
    assert words in a["home"]["configuration"]["beds"]["reason"]


def test_home_not_found_degrades_with_a_reason(market):
    resp = post(make_client(market, homes=FakeHomes(record=None)), BODY)
    reason = resp.get_json()["analysis"]["home"]["configuration"]["beds"]["reason"]
    assert "no record was found" in reason


def test_geocoder_failure_still_fails_even_if_homes_would_work(market):
    homes = FakeHomes(home_record())
    resp = post(make_client(market, FakeGeocoder(error=ProviderTimeout()), homes), BODY)
    assert resp.status_code == 504 and homes.calls == []  # no quota spent without a matched address


def test_home_access_denied_degrades_with_a_generic_note_not_config_details(market):
    from dealscope.errors import ProviderAccessDenied

    resp = post(make_client(market, homes=FakeHomes(error=ProviderAccessDenied())), BODY)
    a = resp.get_json()["analysis"]
    reason = a["home"]["configuration"]["beds"]["reason"]
    assert resp.status_code == 200 and "could not be used right now" in reason
    assert "key" not in reason.lower() and "plan" not in reason.lower() and "quota" not in reason
