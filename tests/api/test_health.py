"""Health endpoint tests."""

from tests.api.conftest import BASE, CORE_TABLES


def test_health_returns_200_and_ok(client):
    r = client.get(f"{BASE}/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_health_row_counts_cover_core_tables(client):
    counts = client.get(f"{BASE}/health").json()["db_row_counts"]
    for table in CORE_TABLES:
        assert table in counts
        assert counts[table] > 0


def test_health_has_uptime_and_version(client):
    body = client.get(f"{BASE}/health").json()
    assert body["uptime_seconds"] >= 0
    assert isinstance(body["version"], str) and body["version"]


def test_response_time_header_is_set(client):
    assert "x-process-time-ms" in client.get(f"{BASE}/health").headers
