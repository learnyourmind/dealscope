import json
import logging

import pytest

from dealscope.errors import ProviderTimeout, ProviderUnavailable
from dealscope.provider import Candidate
from tests.conftest import FakeProvider, make_client, retrieved_facts

MANUAL = {
    "address": "100 Example St, Austin, TX",
    "property": {"purchase_price": 400000, "beds": 3, "state": "TX", "hoa_monthly": 0},
    "assumptions": {"monthly_rent": 2800},
}


def post(client, body, **kw):
    return client.post("/analyze", json=body, **kw)


def test_manual_analysis_succeeds_and_matches_golden_numbers(client):
    resp = post(client, MANUAL)
    assert resp.status_code == 200
    a = resp.get_json()["analysis"]
    assert a["financing"]["monthly_principal_interest"]["value"] == 2128.97
    assert a["metrics"]["monthly_cash_flow"]["value"] == -1086.30
    assert a["metrics"]["cap_rate_pct"]["value"] == 3.13
    assert a["metrics"]["cash_on_cash_pct"]["value"] == -16.29
    assert a["breakdown"]["operating_expenses_total"]["value"] == 1757.33
    assert "verdict" not in json.dumps(a).lower()


def test_lookup_single_candidate_succeeds(lookup_client):
    client, provider = lookup_client
    resp = post(client, {"address": "100 Example St"})
    assert resp.status_code == 200
    assert resp.get_json()["analysis"]["property"]["purchase_price"]["kind"] == "retrieved"
    assert [c[0] for c in provider.calls] == ["search", "get_property"]


def test_ambiguous_matches_require_selection_and_never_analyze_first():
    provider = FakeProvider(
        candidates=[Candidate("1", "1 A St"), Candidate("2", "1 A St Unit 2")],
        facts=retrieved_facts(),
    )
    resp = post(make_client(provider), {"address": "1 A St, Austin"})
    body = resp.get_json()
    assert resp.status_code == 422 and body["error"]["code"] == "AMBIGUOUS_MATCH"
    assert [c["id"] for c in body["error"]["candidates"]] == ["1", "2"]
    assert all(call[0] != "get_property" for call in provider.calls)


def test_candidate_id_skips_search():
    provider = FakeProvider(facts=retrieved_facts())
    resp = post(make_client(provider), {"address": "1 A St, Austin", "candidate_id": "2"})
    assert resp.status_code == 200 and provider.calls == [("get_property", "2")]


def test_property_not_found():
    resp = post(make_client(FakeProvider(candidates=[])), {"address": "999 Nowhere Rd"})
    assert resp.status_code == 404 and resp.get_json()["error"]["code"] == "PROPERTY_NOT_FOUND"


def test_missing_price_is_insufficient_data_not_a_fabricated_default():
    provider = FakeProvider(candidates=[Candidate("1", "x")], facts=retrieved_facts(price=None))
    resp = post(make_client(provider), {"address": "100 Example St"})
    err = resp.get_json()["error"]
    assert resp.status_code == 422 and err["code"] == "INSUFFICIENT_DATA"
    assert err["missing"] == ["price"] and err["manual_entry_required"] is True


def test_disabled_provider_asks_for_manual_entry(client):
    resp = post(client, {"address": "100 Example St, Austin, TX"})
    err = resp.get_json()["error"]
    assert (
        resp.status_code == 422
        and err["code"] == "INSUFFICIENT_DATA"
        and err["manual_entry_required"]
    )


@pytest.mark.parametrize(
    "error,status,code",
    [
        (ProviderTimeout(), 504, "PROVIDER_TIMEOUT"),
        (ProviderUnavailable(), 502, "PROVIDER_UNAVAILABLE"),
    ],
)
def test_provider_failures_map_to_status_and_retryable(error, status, code):
    resp = post(make_client(FakeProvider(error=error)), {"address": "100 Example St"})
    body = resp.get_json()["error"]
    assert resp.status_code == status and body["code"] == code and body["retryable"] is True


@pytest.mark.parametrize(
    "body,status,code",
    [
        ({}, 400, "INVALID_REQUEST"),
        ({"address": "100 Example St", "bogus": 1}, 400, "INVALID_REQUEST"),
        (
            {"address": "100 Example St", "assumptions": {"annual_interest_rate_pct": 99}},
            400,
            "OUT_OF_RANGE",
        ),
        (
            {"address": "100 Example St", "assumptions": {"annual_interest_rate_pct": "NaN"}},
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


def test_unexpected_exception_never_leaks_details():
    class Boom(FakeProvider):
        def search(self, address, deadline=None):
            raise RuntimeError("secret-token-123 /etc/passwd")

    resp = post(make_client(Boom()), {"address": "100 Example St"})
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
    resp = client.post("/analyze", json=MANUAL, headers={"Origin": "https://evil.example"})
    assert "Access-Control-Allow-Origin" not in resp.headers


def test_cors_only_for_configured_origin():
    client = make_client(cors_origins=("https://app.example",))
    ok = client.post("/analyze", json=MANUAL, headers={"Origin": "https://app.example"})
    other = client.post("/analyze", json=MANUAL, headers={"Origin": "https://evil.example"})
    assert ok.headers.get("Access-Control-Allow-Origin") == "https://app.example"
    assert "Access-Control-Allow-Origin" not in other.headers


def test_rate_limit_returns_429():
    client = make_client(rate_limit="2/minute")
    codes = [post(client, MANUAL).status_code for _ in range(3)]
    assert codes == [200, 200, 429]
    assert post(client, MANUAL).get_json()["error"]["code"] == "RATE_LIMITED"
    assert client.get("/healthz").status_code == 200  # health is never limited


def test_logs_exclude_address_and_body(caplog):
    client = make_client()
    with caplog.at_level(logging.INFO, logger="dealscope"):
        post(client, MANUAL)
        post(
            client,
            {"address": "77 Secret Lane, Nowhere, ZZ", "assumptions": {"down_payment_pct": 1}},
        )
    text = "\n".join(r.getMessage() for r in caplog.records)
    assert "Example St" not in text and "Secret Lane" not in text and "400000" not in text
    records = [json.loads(r.getMessage()) for r in caplog.records]
    assert {r["status"] for r in records} == {200, 400}
    assert {"request_id", "route", "latency_ms", "error_code"} <= set(records[0])
    assert records[1]["error_code"] == "OUT_OF_RANGE"
