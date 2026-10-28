"""Sector endpoint tests."""

from tests.api.conftest import BASE


def test_sector_list_matches_database(client, db_counts):
    r = client.get(f"{BASE}/sectors")
    assert r.status_code == 200
    assert len(r.json()) == db_counts["sectors"]


def test_sector_list_fields(client):
    row = client.get(f"{BASE}/sectors").json()[0]
    for key in ("sector", "company_count", "median_roe", "median_pe", "median_de"):
        assert key in row


def test_sector_company_counts_add_up(client, db_counts):
    assert (
        sum(s["company_count"] for s in client.get(f"{BASE}/sectors").json())
        == db_counts["companies"]
    )


def test_it_sector_returns_only_it_companies(client, db_counts):
    r = client.get(f"{BASE}/sectors/IT/companies")
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == db_counts["it_companies"]
    assert all(x["sector"] == "Information Technology" for x in rows)


def test_unknown_sector_returns_404(client):
    assert client.get(f"{BASE}/sectors/Nonexistent/companies").status_code == 404
