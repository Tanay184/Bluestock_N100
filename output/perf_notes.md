# Performance notes

Run at 2026-10-29T16:33:57+00:00 (UTC).

## Load test: 10 concurrent screener calls

- 10/10 succeeded; all finished in 0.17 s (slowest 0.16 s). Target 10 s: **PASS**

## API response times (one request each, cold cache for the first screener call)

| Endpoint | Status | ms |
|---|---|---|
| /portfolio/stats | 200 | 128.1 |
| /companies/TCS/tearsheet | 200 | 67.0 |
| /sectors | 200 | 56.2 |
| /companies | 200 | 41.2 |
| /sectors/IT/companies | 200 | 38.6 |
| /peers/IT_Services | 200 | 37.1 |
| /screener?min_roe=15 | 200 | 33.4 |
| /companies/TCS/ratios | 200 | 32.3 |
| /companies/TCS/pl | 200 | 31.4 |
| /market-cap/TCS | 200 | 31.3 |
| /companies/TCS/documents | 200 | 29.1 |
| /companies/TCS/bs | 200 | 29.0 |
| /companies/TCS/peers/compare | 200 | 29.0 |
| /health | 200 | 25.1 |
| /companies/TCS | 200 | 23.5 |
| /companies/TCS/cashflow | 200 | 16.4 |

## Dashboard

- Company Profile load time (server-side): {'TCS': 0.08, 'INFY': 0.12, 'HDFCBANK': 0.07, 'ITC': 0.08, 'RELIANCE': 0.08}. Target under 3 s each: **PASS**
- Screener ROE >= 15 and D/E <= 1: dashboard 49 companies, API 49: **MATCH**

## End to end

- API on port 8000 up: True; dashboard on port 8501 up: True; both at the same time: True

## Bottlenecks and optimisation

- The screener and sector endpoints build a metric snapshot from several tables; it is cached in memory until the database file changes, so only the first call is slow.
- Indexes on company_id and year (and peer group) are created at API start-up (CREATE INDEX IF NOT EXISTS), which keeps per-company queries in the low milliseconds.
- Timings use 127.0.0.1: on Windows the name localhost can add about 2 seconds to every new connection (IPv6 fallback), which would otherwise hide the real response times.
- Live annual-report link validation (documents?validate=true) depends on the network and is off by default.
- The dashboard caches every query for 10 minutes (st.cache_data), so repeat visits are near-instant.
