"""One named regression test per baseline defect in spec §2.1 (BD-xx)."""

import json

from dealscope.errors import ProviderTimeout
from dealscope.provider import Candidate
from tests.conftest import FakeProvider, make_client, retrieved_facts


def _post(client, body):
    return client.post("/analyze", json=body)


def test_bd01_street_suffix_is_not_mistaken_for_the_state():
    # The prototype regex picked "ST" from "123 Main St, Austin, TX".
    provider = FakeProvider(
        candidates=[Candidate("1", "123 Main St, Austin, TX")],
        facts=retrieved_facts(state="TX", address="123 Main St, Austin, TX"),
    )
    body = _post(make_client(provider), {"address": "123 Main St, Austin, TX"}).get_json()
    tax = body["analysis"]["assumptions"]["property_tax_rate_pct"]
    assert body["analysis"]["property"]["state"]["value"] == "TX" and tax["value"] == 1.63


def test_bd02_no_silent_defaults_for_price_state_or_beds():
    for missing in ("price", "beds", "state"):
        provider = FakeProvider(
            candidates=[Candidate("1", "x")], facts=retrieved_facts(**{missing: None})
        )
        resp = _post(make_client(provider), {"address": "100 Example St"})
        assert resp.status_code == 422, missing
        assert missing in resp.get_json()["error"]["missing"]


def test_bd03_upstream_timeout_is_a_distinct_retryable_error():
    resp = _post(make_client(FakeProvider(error=ProviderTimeout())), {"address": "100 Example St"})
    assert resp.status_code == 504 and resp.get_json()["error"]["retryable"] is True


def test_bd04_errors_do_not_leak_exception_text_and_use_correct_statuses():
    client = make_client()
    resp = client.post("/analyze", data="not json", content_type="text/plain")
    assert resp.status_code == 400 and "NoneType" not in resp.get_data(as_text=True)
    assert client.get("/missing").status_code == 404


def test_bd05_ambiguous_match_is_not_resolved_by_taking_the_first_result():
    provider = FakeProvider(
        candidates=[Candidate("1", "A"), Candidate("2", "B")], facts=retrieved_facts()
    )
    resp = _post(make_client(provider), {"address": "1 A St"})
    assert resp.status_code == 422 and not any(c[0] == "get_property" for c in provider.calls)


def test_bd06_cors_is_not_open_to_all_origins():
    resp = _post(make_client(), {"address": "x"})
    assert "Access-Control-Allow-Origin" not in resp.headers


def test_bd07_root_page_is_a_real_interface_not_a_placeholder():
    html = make_client().get("/").get_data(as_text=True)
    assert "Your original HTML" not in html and "<form" in html and "<h1" in html


def test_bd08_no_buy_caution_verdict_is_emitted():
    body = _post(
        make_client(),
        {
            "address": "100 Example St",
            "property": {"purchase_price": 100000, "beds": 3, "state": "OH"},
            "assumptions": {"monthly_rent": 5000},
        },
    ).get_json()
    text = json.dumps(body).upper()
    assert body["success"] is True and "BUY" not in text and "CAUTION" not in text
