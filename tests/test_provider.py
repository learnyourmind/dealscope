"""Census geocoder adapter and bundled market data. The network is never contacted.

Payloads are synthetic but follow the shape verified against the live Census Geocoder.
"""

import json
from pathlib import Path

import pytest
import requests

from dealscope.errors import (
    InsufficientData,
    ProviderRateLimited,
    ProviderTimeout,
    ProviderUnavailable,
)
from dealscope.provider import (
    CensusGeocoder,
    DisabledGeocoder,
    MarketData,
    build_geocoder,
)


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


def match(text, zip="78701", state="TX", county="Travis County"):
    return {
        "matchedAddress": text,
        "addressComponents": {"zip": zip, "state": state},
        "geographies": {"Counties": [{"NAME": county}]},
    }


def body(*matches):
    return {"result": {"addressMatches": list(matches)}}


def geocoder(response=None, exc=None, connect=3, read=8):
    session = FakeSession(response, exc)
    return CensusGeocoder(connect, read, session), session


def test_geocode_returns_normalized_location_and_uses_timeouts():
    g, session = geocoder(FakeResponse(body=body(match("100 EXAMPLE ST, AUSTIN, TX, 78701"))))
    (location,) = g.geocode("100 example st austin")
    assert (location.address, location.zip, location.state, location.county) == (
        "100 EXAMPLE ST, AUSTIN, TX, 78701",
        "78701",
        "TX",
        "Travis County",
    )
    url, params, timeout = session.calls[0]
    assert "geocoding.geo.census.gov" in url and params["address"] == "100 example st austin"
    assert timeout == (3, 8)


def test_geocode_multiple_matches_deduplicated_and_capped():
    matches = [match(f"{n} A ST, AUSTIN, TX, 78701") for n in range(1, 9)] + [
        match("1 A ST, AUSTIN, TX, 78701")
    ]
    g, _ = geocoder(FakeResponse(body=body(*matches)))
    result = g.geocode("a st")
    assert len(result) == 5 and len({r.address for r in result}) == 5


def test_geocode_no_match_is_empty_list_not_an_error():
    g, _ = geocoder(FakeResponse(body=body()))
    assert g.geocode("nowhere") == []


def test_geocode_tolerates_missing_optional_fields():
    g, _ = geocoder(
        FakeResponse(
            body=body(
                {"matchedAddress": "1 B ST", "addressComponents": {"zip": "ABC", "state": "Texas"}}
            )
        )
    )
    (location,) = g.geocode("x")
    assert location.zip is None and location.state is None and location.county is None


@pytest.mark.parametrize(
    "response,exc,expected",
    [
        (FakeResponse(429, {}), None, ProviderRateLimited),
        (FakeResponse(403, {}), None, ProviderRateLimited),
        (FakeResponse(500, {}), None, ProviderUnavailable),
        (FakeResponse(404, {}), None, ProviderUnavailable),
        (FakeResponse(raw=b"<html>blocked</html>"), None, ProviderUnavailable),
        (FakeResponse(raw=b"[1, 2]"), None, ProviderUnavailable),
        (FakeResponse(body={"result": "nope"}), None, ProviderUnavailable),
        (FakeResponse(raw=b"x" * (2 * 1024 * 1024 + 1)), None, ProviderUnavailable),
        (None, requests.Timeout(), ProviderTimeout),
        (None, requests.ConnectTimeout(), ProviderTimeout),
        (None, requests.ConnectionError("boom"), ProviderUnavailable),
    ],
)
def test_upstream_failures_map_to_safe_domain_errors(response, exc, expected):
    g, _ = geocoder(response, exc)
    with pytest.raises(expected) as caught:
        g.geocode("x")
    assert "boom" not in caught.value.message and "blocked" not in caught.value.message


def test_expired_deadline_raises_timeout_without_calling_upstream():
    g, session = geocoder(FakeResponse(body=body()))
    with pytest.raises(ProviderTimeout):
        g.geocode("x", deadline=0.0)
    assert session.calls == []


def test_build_geocoder_selection():
    assert isinstance(build_geocoder("census", 3, 8), CensusGeocoder)
    assert isinstance(build_geocoder("anything-else", 3, 8), DisabledGeocoder)
    with pytest.raises(ProviderUnavailable):
        DisabledGeocoder().geocode("x")


# ── market data ─────────────────────────────────────────────────────────────


def test_market_lookup_returns_rent_value_and_provenance(market):
    m = market.lookup("78701")
    assert (m.rent, m.home_value, m.state) == (3177.0, 650693.0, "TX")
    assert m.rent_as_of == "2026-09" and "ZORI" in m.rent_source


def test_market_lookup_with_missing_rent_keeps_value(market):
    m = market.lookup("59001")
    assert m.rent is None and m.home_value == 448166.0


def test_market_lookup_unknown_zip_is_insufficient_data_not_a_default(market):
    with pytest.raises(InsufficientData):
        market.lookup("00000")


def test_unreadable_market_file_is_provider_unavailable(tmp_path):
    with pytest.raises(ProviderUnavailable):
        MarketData(tmp_path / "missing.json").lookup("78701")


def test_bundled_snapshot_is_present_and_plausible():
    data = json.loads((Path(__file__).parent.parent / "data" / "zip_market.json").read_text())
    assert len(data["zips"]) > 20_000
    assert data["rent"]["as_of"][:2] == "20" and data["value"]["as_of"][:2] == "20"
    rent, value, state = data["zips"]["78701"]
    assert 1_000 < rent < 10_000 and 100_000 < value < 3_000_000 and state == "TX"
    assert all(len(z) == 5 and z.isdigit() for z in list(data["zips"])[:500])
