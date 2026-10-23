import pytest

from app import create_app
from dealscope.analysis import Fact, PropertyFacts
from dealscope.config import Config
from dealscope.provider import Candidate, PropertyProvider


class FakeProvider(PropertyProvider):
    """Test double: no network. Configure `candidates`, `facts`, or `error`."""

    name = "fake"

    def __init__(self, candidates=None, facts=None, error=None):
        self.candidates = candidates if candidates is not None else []
        self.facts = facts
        self.error = error
        self.calls = []

    def search(self, address, deadline=None):
        self.calls.append(("search", address))
        if self.error:
            raise self.error
        return self.candidates

    def get_property(self, candidate, deadline=None):
        self.calls.append(("get_property", candidate.id))
        if self.error:
            raise self.error
        return self.facts


def retrieved_facts(
    price=400000, beds=3, state="TX", hoa=0.0, address="100 Example St, Austin, TX"
):
    def f(v):
        return None if v is None else Fact(v, "retrieved", "fake", "2026-01-01T00:00:00+00:00")

    return PropertyFacts(
        address=f(address), price=f(price), beds=f(beds), state=f(state), hoa_monthly=f(hoa)
    )


def make_client(provider=None, **config):
    cfg = Config(rate_limit=config.pop("rate_limit", ""), **config)
    app = create_app(cfg, provider)
    app.config["TESTING"] = False  # exercise real error handlers
    return app.test_client()


@pytest.fixture()
def client():
    return make_client()


@pytest.fixture()
def lookup_client():
    provider = FakeProvider(
        candidates=[Candidate("111", "100 Example St, Austin, TX")], facts=retrieved_facts()
    )
    return make_client(provider), provider
