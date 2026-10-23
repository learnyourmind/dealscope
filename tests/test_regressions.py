"""One named regression test per baseline defect in spec §2.1 (BD-xx)."""

import json

from dealscope.errors import ProviderTimeout
from tests.conftest import FakeGeocoder, loc, make_client


def _post(client, body):
    return client.post("/analyze", json=body)


def test_bd01_street_suffix_is_not_mistaken_for_the_state(market):
    # The prototype regex picked "ST" from "123 Main St, Austin, TX".
    geo = FakeGeocoder([loc("123 MAIN ST, AUSTIN, TX, 78701", state="TX")])
    body = _post(make_client(market, geo), {"address": "123 Main St, Austin, TX"}).get_json()
    assert body["analysis"]["location"]["state"] == "TX"
    assert body["analysis"]["assumptions"]["property_tax_rate_pct"]["value"] == 1.63


def test_bd02_no_silent_defaults_when_area_data_is_missing(market):
    geo = FakeGeocoder([loc(zip="59001", state="MT")])
    resp = _post(make_client(market, geo), {"address": "1 Main St, Billings, MT"})
    assert resp.status_code == 422 and resp.get_json()["error"]["code"] == "INSUFFICIENT_DATA"


def test_bd03_upstream_timeout_is_a_distinct_retryable_error(market):
    resp = _post(
        make_client(market, FakeGeocoder(error=ProviderTimeout())), {"address": "100 Example St"}
    )
    assert resp.status_code == 504 and resp.get_json()["error"]["retryable"] is True


def test_bd04_errors_do_not_leak_exception_text_and_use_correct_statuses(client):
    resp = client.post("/analyze", data="not json", content_type="text/plain")
    assert resp.status_code == 400 and "NoneType" not in resp.get_data(as_text=True)
    assert client.get("/missing").status_code == 404


def test_bd05_ambiguous_match_is_not_resolved_by_taking_the_first_result(market):
    geo = FakeGeocoder([loc("1 A ST, AUSTIN, TX, 78701"), loc("1 A ST, AUSTIN, TX, 78702")])
    resp = _post(make_client(market, geo), {"address": "1 A St"})
    assert resp.status_code == 422 and resp.get_json()["error"]["code"] == "AMBIGUOUS_MATCH"


def test_bd06_cors_is_not_open_to_all_origins(client):
    resp = _post(client, {"address": "x"})
    assert "Access-Control-Allow-Origin" not in resp.headers


def test_bd07_root_page_is_a_real_interface_not_a_placeholder(client):
    html = client.get("/").get_data(as_text=True)
    assert "Your original HTML" not in html and "<form" in html and "<h1" in html


def test_bd08_no_buy_caution_verdict_is_emitted(client):
    body = _post(client, {"address": "100 Example St, Austin, TX"}).get_json()
    assert body["success"] is True
    assert '"verdict"' not in json.dumps(body).lower()
