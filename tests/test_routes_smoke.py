"""Route smoke tests. No network access."""

import requests

import app as app_module
from tests.conftest import make_client


def test_index_renders_search_form(client):
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "<form" in html and "Find my number" in html and "not advice" in html.lower()
    assert 'id="purchase_price"' not in html  # address is the only required input


def test_healthz_is_ok_reports_version_and_never_calls_network(monkeypatch, market):
    def _no_network(*args, **kwargs):
        raise AssertionError("/healthz must not touch the network")

    monkeypatch.setattr(requests.Session, "request", _no_network)
    client = make_client(market, app_version="abc1234")

    resp = client.get("/healthz")

    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok", "version": "abc1234"}


def test_module_level_app_exists_for_gunicorn_and_vercel():
    assert app_module.app.url_map.bind("localhost").match("/healthz")[0] == "healthz"


def test_head_request_to_root_is_not_treated_as_a_submission(client):
    assert client.head("/").status_code == 200
