from dealscope.provider import Candidate
from dealscope.ratelimit import RateLimiter, parse_rate
from tests.conftest import FakeProvider, make_client, retrieved_facts

FORM = {
    "address": "100 Example St, Austin, TX",
    "purchase_price": "400,000",
    "beds": "3",
    "state": "tx",
    "hoa_monthly": "0",
    "down_payment_pct": "20",
    "annual_interest_rate_pct": "7",
    "loan_term_years": "30",
    "monthly_rent": "2800",
}


def test_form_post_renders_results_without_javascript(client):
    resp = client.post("/", data=FORM)
    html = resp.get_data(as_text=True)
    assert resp.status_code == 200
    assert "Results for 100 Example St, Austin, TX" in html
    assert "−$1,086.30" in html and "3.13%" in html and "−16.29%" in html
    assert "Negative" in html  # status is text, not color alone
    assert "You entered" in html and "Estimate" in html
    assert "No buy/sell recommendation" in html and "Not advice" in html


def test_unavailable_values_are_labeled_not_zero(client):
    data = dict(FORM, hoa_monthly="", beds="7", monthly_rent="")
    html = client.post("/", data=data).get_data(as_text=True)
    assert "Unavailable" in html
    assert "(qualified)" not in html  # nothing to qualify when rent is withheld


def test_missing_hoa_marks_results_qualified(client):
    html = client.post("/", data=dict(FORM, hoa_monthly="")).get_data(as_text=True)
    assert "(qualified)" in html and "HOA fees were unavailable" in html


def test_validation_error_preserves_inputs_and_is_announced(client):
    resp = client.post("/", data=dict(FORM, annual_interest_rate_pct="99"))
    html = resp.get_data(as_text=True)
    assert resp.status_code == 400
    assert 'role="alert"' in html and "annual_interest_rate_pct" in html
    assert 'value="99"' in html and 'value="100 Example St, Austin, TX"' in html


def test_non_numeric_form_input_is_a_clear_error(client):
    resp = client.post("/", data=dict(FORM, purchase_price="lots"))
    assert resp.status_code == 400 and "must be a number" in resp.get_data(as_text=True)


def test_disabled_lookup_shows_manual_fields_required(client):
    html = client.get("/").get_data(as_text=True)
    assert "Automatic property lookup is turned off" in html
    assert 'id="purchase_price"' in html and "required" in html
    assert "not sent to any third party" in html


def test_ambiguous_match_shows_chooser_and_selection_works():
    provider = FakeProvider(
        candidates=[
            Candidate("1", "1 A St, Austin, TX"),
            Candidate("2", "1 A St Unit 2, Austin, TX"),
        ],
        facts=retrieved_facts(),
    )
    client = make_client(provider)
    resp = client.post("/", data={"address": "1 A St", "down_payment_pct": "20"})
    html = resp.get_data(as_text=True)
    assert resp.status_code == 422 and "Choose the right property" in html
    assert 'name="candidate_id" value="2"' in html
    assert "sent to the property data provider" in html

    chosen = client.post("/", data={"address": "1 A St", "candidate_id": "2"})
    assert chosen.status_code == 200 and "Results for" in chosen.get_data(as_text=True)


def test_provider_error_shows_retry_guidance_and_reference():
    from dealscope.errors import ProviderTimeout

    client = make_client(FakeProvider(error=ProviderTimeout()))
    resp = client.post("/", data={"address": "100 Example St"})
    html = resp.get_data(as_text=True)
    assert resp.status_code == 504 and "try again" in html and "Reference:" in html


def test_page_has_accessibility_basics(client):
    html = client.get("/").get_data(as_text=True)
    assert '<html lang="en">' in html and 'class="skip"' in html and "<main" in html
    assert html.count("<h1") == 1
    for field in ("address", "down_payment_pct", "annual_interest_rate_pct", "loan_term_years"):
        assert f'for="{field}"' in html


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
