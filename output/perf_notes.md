# Performance notes

Run at 2026-10-28T05:01:44+00:00 (UTC).

## Load test: 10 concurrent screener calls

- 10/10 succeeded; all finished in 0.16 s (slowest 0.15 s). Target 10 s: **PASS**

## API response times (one request each, cold cache for the first screener call)

| Endpoint | Status | ms |
|---|---|---|
| /portfolio/stats | 200 | 124.2 |
| /companies/TCS/peers/compare | 200 | 38.7 |
| /companies/TCS/tearsheet | 200 | 36.3 |
| /sectors | 200 | 35.1 |
| /companies/TCS/ratios | 200 | 34.1 |
| /companies/TCS/pl | 200 | 32.3 |
| /screener?min_roe=15 | 200 | 31.5 |
| /companies/TCS/bs | 200 | 31.2 |
| /companies/TCS/documents | 200 | 30.2 |
| /companies/TCS/cashflow | 200 | 29.1 |
| /peers/IT_Services | 200 | 27.9 |
| /sectors/IT/companies | 200 | 26.9 |
| /market-cap/TCS | 200 | 23.0 |
| /companies/TCS | 200 | 17.2 |
| /companies | 200 | 17.0 |
| /health | 200 | 5.4 |

## Dashboard

- Company Profile load time (server-side): {'TCS': 0.07, 'INFY': 0.12, 'HDFCBANK': 0.08, 'ITC': 0.05, 'RELIANCE': 0.08}. Target under 3 s each: **PASS**
- Screener ROE >= 15 and D/E <= 1: dashboard 38 companies, API 38: **MATCH**

## End to end

- API on port 8000 up: True; dashboard on port 8501 up: True; both at the same time: True

## Bottlenecks and optimisation

- The screener and sector endpoints build a metric snapshot from several tables; it is cached in memory until the database file changes, so only the first call is slow.
- Indexes on company_id and year (and peer group) are created at API start-up (CREATE INDEX IF NOT EXISTS), which keeps per-company queries in the low milliseconds.
- Timings use 127.0.0.1: on Windows the name localhost can add about 2 seconds to every new connection (IPv6 fallback), which would otherwise hide the real response times.
- Live annual-report link validation (documents?validate=true) depends on the network and is off by default.
- The dashboard caches every query for 10 minutes (st.cache_data), so repeat visits are near-instant.
