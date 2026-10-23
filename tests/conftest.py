import json

import pytest

from app import create_app
from dealscope.config import Config
from dealscope.provider import Geocoder, Location, MarketData

DATA = {
    "rent": {"name": "Zillow Observed Rent Index (ZORI)", "as_of": "2026-09"},
    "value": {"name": "Zillow Home Value Index (ZHVI)", "as_of": "2026-09"},
    "zips": {
        "78701": [3177, 650693, "TX"],
        "44102": [1356, 130988, "OH"],
        "59001": [None, 448166, "MT"],
        "20500": [3000, 700000, "DC"],
    },
}


def loc(
    address="100 EXAMPLE ST, AUSTIN, TX, 78701", zip="78701", state="TX", county="Travis County"
):
    return Location(address=address, zip=zip, state=state, county=county)


class FakeGeocoder(Geocoder):
    """Test double: no network. Configure `locations` or `error`."""

    name = "fake"

    def __init__(self, locations=None, error=None):
        self.locations = [loc()] if locations is None else locations
        self.error = error
        self.calls = []

    def geocode(self, address, deadline=None):
        self.calls.append(address)
        if self.error:
            raise self.error
        return self.locations


@pytest.fixture()
def market(tmp_path):
    path = tmp_path / "zip_market.json"
    path.write_text(json.dumps(DATA))
    return MarketData(path)


def make_client(market, geocoder=None, **config):
    cfg = Config(rate_limit=config.pop("rate_limit", ""), **config)
    app = create_app(cfg, geocoder or FakeGeocoder(), market)
    app.config["TESTING"] = False  # exercise real error handlers
    return app.test_client()


@pytest.fixture()
def client(market):
    return make_client(market)
