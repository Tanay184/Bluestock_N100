"""Company endpoint tests."""

import pytest

from tests.api.conftest import BASE


def test_companies_returns_every_company(client, db_counts):
    r = client.get(f"{BASE}/companies")
    assert r.status_code == 200
    assert len(r.json()) == db_counts["companies"]


def test_company_list_fields(client):
    first = client.get(f"{BASE}/companies").json()[0]
    for key in (
        "id",
        "company_name",
        "broad_sector",
        "sub_sector",
        "roe_pct",
        "roce_pct",
    ):
        assert key in first


def test_tcs_profile(client):
    r = client.get(f"{BASE}/companies/TCS")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == "TCS"
    assert body["sector"]["broad_sector"] == "Information Technology"
    assert body["latest_kpis"]["year"] >= "2023-03"


def test_ticker_is_case_insensitive(client):
    assert client.get(f"{BASE}/companies/tcs").json()["id"] == "TCS"


def test_invalid_ticker_returns_404(client):
    assert client.get(f"{BASE}/companies/INVALID").status_code == 404


def test_search_filter(client):
    ids = [
        c["id"]
        for c in client.get(f"{BASE}/companies", params={"search": "tcs"}).json()
    ]
    assert "TCS" in ids and len(ids) < 5


def test_sector_filter_accepts_it_alias(client):
    rows = client.get(f"{BASE}/companies", params={"sector": "IT"}).json()
    assert rows and all(r["broad_sector"] == "Information Technology" for r in rows)


@pytest.mark.parametrize("part", ["pl", "bs", "cashflow", "ratios"])
def test_history_endpoints_return_arrays(client, part):
    r = client.get(f"{BASE}/companies/TCS/{part}")
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, list) and len(body) >= 5
    assert [row["year"] for row in body] == sorted(row["year"] for row in body)


def test_year_range_filter(client):
    rows = client.get(
        f"{BASE}/companies/TCS/pl",
        params={"from_year": "2020-03", "to_year": "2022-03"},
    ).json()
    assert rows and all("2020-03" <= r["year"] <= "2022-03" for r in rows)


@pytest.mark.parametrize(
    "bad",
    [
        {"from_year": "2020"},
        {"to_year": "03-2020"},
        {"from_year": "2024-03", "to_year": "2020-03"},
    ],
)
def test_bad_year_parameters_return_400(client, bad):
    assert client.get(f"{BASE}/companies/TCS/pl", params=bad).status_code == 400


def test_history_unknown_ticker_404(client):
    assert client.get(f"{BASE}/companies/NOPE/cashflow").status_code == 404


def test_tcs_ratios_cover_ten_plus_years(client, db_counts):
    body = client.get(f"{BASE}/companies/TCS/ratios").json()
    assert len(body) == db_counts["tcs_ratio_years"]
    assert len(body) >= 10


def test_single_year_ratio_and_missing_year(client):
    one = client.get(f"{BASE}/companies/TCS/ratios", params={"year": "2024-03"})
    assert one.status_code == 200 and len(one.json()) == 1
    assert (
        client.get(
            f"{BASE}/companies/TCS/ratios", params={"year": "1999-03"}
        ).status_code
        == 404
    )
    assert (
        client.get(f"{BASE}/companies/TCS/ratios", params={"year": "99"}).status_code
        == 400
    )


def test_tearsheet_unknown_ticker_404(client):
    assert client.get(f"{BASE}/companies/NOPE/tearsheet").status_code == 404


def test_tearsheet_download_is_pdf_when_generated(client):
    r = client.get(f"{BASE}/companies/TCS/tearsheet")
    if r.status_code == 404:
        pytest.skip("tearsheets not generated yet")
    assert r.headers["content-type"] == "application/pdf"
    assert r.content[:4] == b"%PDF"
