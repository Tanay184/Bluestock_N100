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