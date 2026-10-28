# Nifty 100 Financial Intelligence Platform

Analytics platform for 92 Nifty 100 companies: ETL -> SQLite -> 50+ KPIs -> screener, peers, valuation -> Streamlit dashboard.
Stock prices and market caps in the source data are **simulated**.

## Setup
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Build the data (run in this order from the project root)
```powershell
python -m src.etl.loader          # Excel -> data/nifty100.db, load_audit.csv, validation_failures.csv
python -m src.analytics.run_ratios  # financial_ratios, capital_allocation.csv, ratio_edge_cases.log
python -m src.analytics.screener    # output/screener_output.xlsx
python -m src.analytics.peer        # peer_percentiles, peer_comparison.xlsx, reports/radar_charts/
python -m src.analytics.valuation   # valuation_summary.xlsx, valuation_flags.csv
pytest tests/ -q                    # unit tests
```

## Run the dashboard
```powershell
streamlit run src/dashboard/app.py
```
Opens at http://localhost:8501.

| Screen | What it does |
|---|---|
| Home | 6 market KPI tiles, sector donut, top 5 by quality score, year selector (2019-2024) |
| Company Profile | Search by name/ticker; KPI tiles, revenue/profit bars, ROE/ROCE chart, pros and cons |
| Screener | 10 sliders, 6 presets, live results, CSV download |
| Peer Comparison | Radar vs peer-group average and side-by-side KPI table (benchmark highlighted) |
| Trend Analysis | Up to 3 metrics over 10 years with YoY % labels |
| Sector Analysis | Revenue vs ROE bubble chart and sector vs Nifty 100 median KPIs |
| Capital Allocation | Treemap of 8 cash-flow patterns, company list per pattern |
| Annual Reports | BSE annual report links per year, optional link check |

## QA
```powershell
python scripts\dashboard_smoke.py --all   # runs every screen for all 92 tickers
```
## Clustering, REST API and final QA (Sprint 6)

### Clustering and portfolio statistics
```powershell
python -m src.analytics.clustering
```
Writes `output/cluster_labels.csv` (5 clusters, 92 companies), `cluster_profile.csv`, `outlier_report.csv`, `portfolio_stats.csv`,
`reports/elbow_plot.png` and `reports/correlation_heatmap.png`. Cluster names can be overridden in `config/cluster_names.yaml`.

### REST API
```powershell
uvicorn src.api.main:app --port 8000
```
Interactive documentation: http://localhost:8000/docs. Specification: `docs/openapi.json`; Postman collection: `docs/postman_collection.json`
(regenerate with `python scripts\export_api_spec.py`). All routes are under `/api/v1`:

| Endpoint | Purpose |
|---|---|
| `GET /health` | Status, row counts of every table, uptime, version |
| `GET /companies` | All companies (filters: `sector`, `market_cap_category`, `search`) |
| `GET /companies/{ticker}` | Company profile with latest KPIs |
| `GET /companies/{ticker}/pl`, `/bs`, `/cashflow` | Statement history (`from_year`, `to_year` as YYYY-MM) |
| `GET /companies/{ticker}/ratios` | KPIs per year (optional `year`) |
| `GET /companies/{ticker}/tearsheet` | Tearsheet PDF download |
| `GET /screener` | Ranked screener (`min_roe`, `max_de`, `min_fcf`, `sector`, `min_rev_cagr_5yr`, `min_pat_cagr_5yr`, `max_pe`) |
| `GET /sectors`, `/sectors/{sector}/companies` | Sector medians and members |
| `GET /peers/{group}`, `/companies/{ticker}/peers/compare` | Peer percentiles and radar data |
| `GET /market-cap/{ticker}` | Valuation history (simulated data) |
| `GET /portfolio/stats` | P10 to P90 for 10 KPIs |
| `GET /companies/{ticker}/documents` | Annual report links (`validate=true` for a live link check) |

Example: `curl.exe "http://localhost:8000/api/v1/screener?min_roe=15&max_de=1"`

### Tests and QA
```powershell
pytest tests/ -q                                   # full suite
pytest tests/ --html=reports/pytest_report.html    # HTML report
python scripts\dashboard_smoke.py --all            # every dashboard screen for all tickers
python scripts\perf_check.py                       # load test and end-to-end check (stop running servers first)
python scripts\check_docstrings.py                 # every public function needs a docstring
python scripts\finalize.py --manual-pass AC-09,AC-10   # 20 acceptance gates, checklist PDF, archive
```
Documentation: `docs/analyst_guide.pdf` (generate with `python -m src.reports.analyst_guide`), `docs/acceptance_checklist.pdf`.
