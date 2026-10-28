"""Peer, valuation, portfolio and document endpoint tests."""

import pytest

from tests.api.conftest import BASE


def first_group(client):
    """Name of a peer group that exists in the database."""
    import sqlite3
    from contextlib import closing

    from src.etl.loader import DB_PATH

    with closing(sqlite3.connect(DB_PATH)) as conn:
        return conn.execute(
            "SELECT DISTINCT peer_group_name FROM peer_groups ORDER BY 1"
        ).fetchone()[0]


def test_peer_group_lists_members_with_percentiles(client):
    name = first_group(client)
    r = client.get(f"{BASE}/peers/{name}")
    assert r.status_code == 200
    body = r.json()
    assert body["companies"] and body["benchmark"]
    assert all(c["percentile_rank"] for c in body["companies"])


def test_peer_group_name_is_forgiving(client):
    name = first_group(client).replace(" ", "_").lower()
    assert client.get(f"{BASE}/peers/{name}").status_code == 200


def test_unknown_peer_group_404(client):
    assert client.get(f"{BASE}/peers/not-a-group").status_code == 404


def test_peer_compare_returns_eight_axes(client):
    r = client.get(f"{BASE}/companies/TCS/peers/compare")
    if r.status_code == 404:
        pytest.skip("TCS has no peer group in this database")
    body = r.json()
    assert len(body["axes"]) == 8
    assert set(body["company"]) == set(body["peer_group_average"]) == set(body["axes"])
    assert body["benchmark"]["company_id"]


def test_peer_compare_unknown_ticker_404(client):
    assert client.get(f"{BASE}/companies/NOPE/peers/compare").status_code == 404


def test_market_cap_history(client):
    r = client.get(f"{BASE}/market-cap/TCS")
    assert r.status_code == 200
    body = r.json()
    assert body["simulated"] is True
    assert body["history"] and "pe_ratio" in body["history"][0]
    assert [h["year"] for h in body["history"]] == sorted(
        h["year"] for h in body["history"]
    )


def test_market_cap_unknown_ticker_404(client):
    assert client.get(f"{BASE}/market-cap/NOPE").status_code == 404


def test_portfolio_stats_has_ten_kpis(client):
    rows = client.get(f"{BASE}/portfolio/stats").json()
    assert len(rows) == 10
    for key in ("metric", "P10", "P25", "P50", "P75", "P90", "Mean", "Std"):
        assert key in rows[0]
    assert all(r["P10"] <= r["P50"] <= r["P90"] for r in rows)


def test_documents_default_is_format_check(client):
    r = client.get(f"{BASE}/companies/TCS/documents")
    assert r.status_code == 200
    body = r.json()
    assert body["validation"] == "format"
    assert body["documents"] and all(
        isinstance(d["is_url_valid"], bool) for d in body["documents"]
    )


def test_documents_year_filter_and_bad_year(client):
    rows = client.get(
        f"{BASE}/companies/TCS/documents", params={"from_year": "2022"}
    ).json()["documents"]
    assert all(d["year"] >= 2022 for d in rows)
    assert (
        client.get(
            f"{BASE}/companies/TCS/documents", params={"from_year": "abcd"}
        ).status_code
        == 400
    )


def test_documents_unknown_ticker_404(client):
    assert client.get(f"{BASE}/companies/NOPE/documents").status_code == 404


def test_openapi_lists_all_sixteen_endpoints(client):
    paths = client.get("/openapi.json").json()["paths"]
    assert sum(len(methods) for methods in paths.values()) == 16
