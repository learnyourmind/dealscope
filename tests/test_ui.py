from dealscope.errors import ProviderTimeout
from dealscope.ratelimit import RateLimiter, parse_rate
from tests.conftest import FakeGeocoder, loc, make_client

FORM = {
    "address": "100 Example St, Austin, TX",
    "down_payment_pct": "20",
    "annual_interest_rate_pct": "7",
    "loan_term_years": "30",
    "min_monthly_cash_flow": "100",
}


def test_form_post_renders_results_without_javascript(client):
    resp = client.post("/", data=FORM)
    html = resp.get_data(as_text=True)
    assert resp.status_code == 200
    assert "Up to $" in html and "By bedroom count" in html and "PITI break-even" in html
    assert "Public data" in html and "Estimate" in html  # source type shown for every figure
    assert "Monthly math at the target price" in html and "PITI total" in html
    assert "ZIP 78701" in html and "Zillow" in html and "Census" in html


def test_unknown_hoa_note_is_shown_and_known_hoa_hides_it(client):
    assert "HOA is unknown" in client.post("/", data=FORM).get_data(as_text=True)
    html = client.post("/", data=dict(FORM, hoa_monthly="200")).get_data(as_text=True)
    assert "HOA is unknown" not in html


def test_unreachable_target_is_explained(client):
    html = client.post("/", data=dict(FORM, min_monthly_cash_flow="10000")).get_data(as_text=True)
    assert "Not reachable" in html


def test_validation_error_preserves_inputs_and_is_announced(client):
    resp = client.post("/", data=dict(FORM, annual_interest_rate_pct="99"))
    html = resp.get_data(as_text=True)
    assert resp.status_code == 400
    assert 'role="alert"' in html and "annual_interest_rate_pct" in html
    assert 'value="99"' in html and 'value="100 Example St, Austin, TX"' in html


def test_non_numeric_form_input_is_a_clear_error(client):
    resp = client.post("/", data=dict(FORM, hoa_monthly="lots"))
    assert resp.status_code == 400 and "must be a number" in resp.get_data(as_text=True)


def test_currency_symbols_and_commas_are_accepted(client):
    resp = client.post("/", data=dict(FORM, min_monthly_cash_flow="$1,000", hoa_monthly="$150"))
    assert resp.status_code == 200


def test_disabled_lookup_is_explained(market):
    from dealscope.provider import DisabledGeocoder

    client = make_client(market, DisabledGeocoder())
    html = client.get("/").get_data(as_text=True)
    assert "Address lookup is switched off" in html
    resp = client.post("/", data=FORM)
    assert resp.status_code == 502 and "turned off" in resp.get_data(as_text=True)


def test_ambiguous_match_shows_picks_and_selection_works(market):
    geo = FakeGeocoder([loc("1 A ST, AUSTIN, TX, 78701"), loc("1 A ST, AUSTIN, TX, 78702")])
    client = make_client(market, geo)
    resp = client.post("/", data=dict(FORM, address="1 A St"))
    html = resp.get_data(as_text=True)
    assert resp.status_code == 422 and "Which address did you mean?" in html
    assert 'name="pick" value="1 A ST, AUSTIN, TX, 78702"' in html

    geo.locations = [loc("1 A ST, AUSTIN, TX, 78702", zip="78701")]
    chosen = client.post("/", data=dict(FORM, pick="1 A ST, AUSTIN, TX, 78702"))
    assert chosen.status_code == 200 and "Results" in chosen.get_data(as_text=True)
    assert geo.calls[-1] == "1 A ST, AUSTIN, TX, 78702"  # the pick replaced the typed address


def test_provider_error_shows_retry_guidance_and_reference(market):
    client = make_client(market, FakeGeocoder(error=ProviderTimeout()))
    resp = client.post("/", data=FORM)
    html = resp.get_data(as_text=True)
    assert resp.status_code == 504 and "try again" in html.lower() and "Reference:" in html


def test_page_has_accessibility_basics(client):
    html = client.get("/").get_data(as_text=True)
    assert '<html lang="en">' in html and 'class="skip"' in html and "<main" in html
    assert html.count("<h1") == 1
    for field in (
        "address",
        "down_payment_pct",
        "annual_interest_rate_pct",
        "loan_term_years",
        "min_monthly_cash_flow",
        "hoa_monthly",
    ):
        assert f'for="{field}"' in html
    assert "fonts.googleapis" not in html and "cdn." not in html  # no third-party requests


def test_user_input_is_escaped(client):
    resp = client.post("/", data=dict(FORM, address="<script>alert(1)</script> 100 Main St"))
    assert "<script>alert(1)</script>" not in resp.get_data(as_text=True)


def test_rate_limiter_window():
    limiter = RateLimiter(2, 60)
    assert [limiter.allow("a", now=t) for t in (0, 1, 2)] == [True, True, False]
    assert limiter.allow("b", now=2) is True
    assert limiter.allow("a", now=61) is True


def test_parse_rate():
    assert parse_rate("20/minute") == (20, 60)
    assert parse_rate("5 / hour") == (5, 3600)
    assert parse_rate("") is None and parse_rate("lots") is None
