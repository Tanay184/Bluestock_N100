"""Screener endpoint tests."""

import pytest

from tests.api.conftest import BASE


def test_min_roe_filter(client):
    rows = client.get(f"{BASE}/screener", params={"min_roe": 15}).json()
    assert all(r["roe"] >= 15 for r in rows)


def test_combined_filters_hold(client):
    rows = client.get(
        f"{BASE}/screener", params={"min_roe": 10, "max_de": 1, "min_fcf": 0}
    ).json()
    assert all(
        r["roe"] >= 10
        and (r["de"] <= 1 or r["broad_sector"] == "Financials")
        and r["fcf"] >= 0
        for r in rows
    )


def test_results_ranked_by_score(client):
    rows = client.get(f"{BASE}/screener").json()
    scores = [r["screen_score"] for r in rows]
    assert scores == sorted(scores, reverse=True)
    assert [r["rank"] for r in rows] == list(range(1, len(rows) + 1))


def test_no_filters_returns_all_companies(client, db_counts):
    assert len(client.get(f"{BASE}/screener").json()) == db_counts["companies"]


@pytest.mark.parametrize(
    "params",
    [{"min_roe": "abc"}, {"max_de": "x1"}, {"min_fcf": "nan"}, {"max_pe": "inf"}],
)
def test_invalid_numbers_return_400(client, params):
    assert client.get(f"{BASE}/screener", params=params).status_code == 400


def test_unknown_sector_returns_400(client):
    assert (
        client.get(f"{BASE}/screener", params={"sector": "Nonexistent"}).status_code
        == 400
    )


def test_sector_filter(client):
    rows = client.get(f"{BASE}/screener", params={"sector": "IT"}).json()
    assert rows and all(r["broad_sector"] == "Information Technology" for r in rows)


def test_extreme_thresholds_return_empty_list_not_error(client):
    r = client.get(f"{BASE}/screener", params={"min_roe": 10000})
    assert r.status_code == 200 and r.json() == []
