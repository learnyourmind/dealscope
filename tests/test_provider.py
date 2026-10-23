"""Redfin adapter tests with synthetic payloads. The live service is never contacted.

Payload shapes are written from the field names the adapter reads; they are NOT recordings
of real responses (plan P0-1 forbids probing the live endpoint until terms are reviewed).
"""

import json

import pytest
import requests

from dealscope.errors import (
    ProviderRateLimited,
    ProviderTimeout,
    ProviderUnavailable,
)
from dealscope.provider import Candidate, DisabledProvider, RedfinProvider, build_provider


class FakeResponse:
    def __init__(self, status=200, body=None, raw=None):
        self.status_code = status
        self.content = raw if raw is not None else json.dumps(body).encode()


class FakeSession:
    def __init__(self, response=None, exc=None):
        self.headers = {}
        self.response, self.exc, self.calls = response, exc, []

    def get(self, url, params=None, timeout=None):
        self.calls.append((url, params, timeout))
        if self.exc:
            raise self.exc
        return self.response


def provider(response=None, exc=None):
    return RedfinProvider(session=FakeSession(response, exc)), None


def row(pid, name="100 Example St", sub="Austin, TX"):
    return {"id": f"1_{pid}", "name": name, "subName": sub, "url": f"/TX/Austin/x/home/{pid}"}


def search_payload(*rows, exact=None):
    payload = {"exactMatch": exact} if exact else {"sections": [{"rows": list(rows)}]}
    return {"payload": payload}


def test_search_returns_normalized_candidates_and_uses_timeouts():
    session = FakeSession(FakeResponse(body=search_payload(row(111), row(222))))
    result = RedfinProvider(3, 8, session).search("100 Example St")
    assert [c.id for c in result] == ["111", "222"]
    assert result[0].display == "100 Example St, Austin, TX"
    assert session.calls[0][2] == (3, 8)


def test_search_exact_match_is_single_candidate():
    session = FakeSession(FakeResponse(body=search_payload(exact=row(111))))
    assert len(RedfinProvider(session=session).search("x")) == 1


def test_search_ignores_non_property_rows_and_caps_results():
    rows = [{"id": "2_9", "name": "Austin", "url": "/city/9/TX/Austin"}] + [
        row(i) for i in range(1, 9)
    ]
    result = RedfinProvider(session=FakeSession(FakeResponse(body=search_payload(*rows)))).search(
        "x"
    )
    assert len(result) == 5 and all(c.id.isdigit() for c in result)


def test_search_empty_is_empty_list_not_error():
    session = FakeSession(FakeResponse(body={"payload": {"sections": []}}))
    assert RedfinProvider(session=session).search("nowhere") == []


def test_redfin_json_prefix_is_stripped():
    raw = b"{}&&" + json.dumps(search_payload(row(111))).encode()
    assert RedfinProvider(session=FakeSession(FakeResponse(raw=raw))).search("x")[0].id == "111"


@pytest.mark.parametrize(
    "response,exc,expected",
    [
        (FakeResponse(429, {}), None, ProviderRateLimited),
        (FakeResponse(403, {}), None, ProviderRateLimited),
        (FakeResponse(500, {}), None, ProviderUnavailable),
        (FakeResponse(404, {}), None, ProviderUnavailable),
        (FakeResponse(raw=b"<html>blocked</html>"), None, ProviderUnavailable),
        (FakeResponse(raw=b"[1, 2]"), None, ProviderUnavailable),
        (FakeResponse(body={"payload": "nope"}), None, ProviderUnavailable),
        (FakeResponse(raw=b"x" * (2 * 1024 * 1024 + 1)), None, ProviderUnavailable),
        (None, requests.Timeout(), ProviderTimeout),
        (None, requests.ConnectTimeout(), ProviderTimeout),
        (None, requests.ConnectionError("boom"), ProviderUnavailable),
    ],
)
def test_upstream_failures_map_to_safe_domain_errors(response, exc, expected):
    with pytest.raises(expected) as caught:
        RedfinProvider(session=FakeSession(response, exc)).search("x")
    assert "boom" not in caught.value.message and "blocked" not in caught.value.message


def test_expired_deadline_raises_timeout_without_calling_upstream():
    session = FakeSession(FakeResponse(body={}))
    with pytest.raises(ProviderTimeout):
        RedfinProvider(session=session).search("x", deadline=0.0)
    assert session.calls == []


def test_get_property_normalizes_and_stamps_provenance():
    body = {
        "payload": {
            "listPrice": {"value": 410000},
            "beds": 3,
            "sqFt": {"value": 1800},
            "hoa": {"value": 55},
            "propertyType": "Single Family",
            "addressSectionInfo": {"state": "tx"},
        }
    }
    facts = RedfinProvider(session=FakeSession(FakeResponse(body=body))).get_property(
        Candidate("111", "100 Example St, Austin, TX")
    )
    assert (facts.price.value, facts.beds.value, facts.state.value, facts.hoa_monthly.value) == (
        410000.0,
        3,
        "TX",
        55.0,
    )
    assert (
        facts.price.kind == "retrieved"
        and facts.price.source == "redfin"
        and facts.price.retrieved_at
    )


def test_get_property_missing_fields_are_none_not_defaults():
    facts = RedfinProvider(
        session=FakeSession(FakeResponse(body={"payload": {"beds": 2}}))
    ).get_property(Candidate("111", "x"))
    assert facts.price is None and facts.state is None and facts.hoa_monthly is None
    assert facts.beds.value == 2


@pytest.mark.parametrize("bad_state", ["Texas", "T", "12", None, 5])
def test_get_property_rejects_malformed_state(bad_state):
    body = {"payload": {"listPrice": {"value": 1}, "addressSectionInfo": {"state": bad_state}}}
    facts = RedfinProvider(session=FakeSession(FakeResponse(body=body))).get_property(
        Candidate("1", "x")
    )
    assert facts.state is None


def test_build_provider_defaults_to_disabled():
    assert isinstance(build_provider("anything-else", 3, 8), DisabledProvider)
    assert isinstance(build_provider("redfin", 3, 8), RedfinProvider)
