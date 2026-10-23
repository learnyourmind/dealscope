"""Baseline route tests for the current app. No network access.

Behavior-pinning tests for known-bad behavior (BD-04) are deliberately avoided;
add real contract tests with plan.md task 1.1/1.8.
"""

import pytest

import app as app_module


@pytest.fixture()
def client():
    app_module.app.config["TESTING"] = True
    return app_module.app.test_client()


def test_index_renders(client):
    resp = client.get("/")
    assert resp.status_code == 200


def test_healthz_is_ok_and_reports_version(client, monkeypatch):
    monkeypatch.setenv("APP_VERSION", "abc1234")

    def _no_network(*args, **kwargs):
        raise AssertionError("/healthz must not call the property provider")

    monkeypatch.setattr(app_module.analyzer.rf.s, "get", _no_network)

    resp = client.get("/healthz")

    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok", "version": "abc1234"}


def test_analyze_rejects_non_json_body(client):
    resp = client.post("/analyze", data="not json", content_type="text/plain")
    assert resp.status_code >= 400
    assert resp.get_json()["success"] is False


def test_analyze_rejects_missing_address(client):
    resp = client.post("/analyze", json={})
    assert resp.status_code >= 400
    assert resp.get_json()["success"] is False
