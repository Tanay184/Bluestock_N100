"""API screener: the D/E maximum does not exclude Financials."""

from tests.api.conftest import BASE


def test_zero_de_cap_keeps_financials_and_drops_levered_non_financials(client):
    rows = client.get(f"{BASE}/screener", params={"max_de": 0}).json()
    assert any(r["broad_sector"] == "Financials" for r in rows)
    assert all(r["broad_sector"] == "Financials" or r["de"] <= 0 for r in rows)


def test_sector_filter_still_applies_with_de_cap(client):
    rows = client.get(
        f"{BASE}/screener", params={"max_de": 1, "sector": "Financials"}
    ).json()
    assert rows and all(r["broad_sector"] == "Financials" for r in rows)
