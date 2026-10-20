# Sprint 4 Retrospective — Dashboard & Valuation

## Delivered
- src/dashboard/app.py, 8 pages (01_home .. 08_reports), utils/db.py (cached, ttl=600), utils/ui.py
- src/analytics/valuation.py, output/valuation_summary.xlsx (92 rows), output/valuation_flags.csv (Caution 14, Discount 30, Fair 48)
- scripts/dashboard_smoke.py, README.md with run instructions and screen descriptions

## QA results
- Streamlit AppTest smoke run: 320 page runs (every company, sector, peer group, year, screener presets and min/max slider extremes): 0 failures
- Company Profile render time <= 0.12 s for TCS, INFY, HDFCBANK, ITC, RELIANCE (gate: 3 s; measured server-side, excludes browser rendering)
- Short-history companies (JIOFIN, LICI, ATGL, ADANIGREEN) show a "only N years of data" note, no crash

## UX decisions
- Missing values display "N/A" (Styler na_rep); CSV export keeps raw numbers
- Screener presets fill sliders; conditions without a slider (e.g. D/E == 0, D/E change) are applied as extra filters and listed on screen
- Home "Average ROE" is capped at the 5th/95th percentile: a few companies have extreme ROE (e.g. NESTLEIND ~118%)
- Capital Allocation uses a dropdown below the treemap to list companies for a pattern
- Annual report link check is opt-in (checkbox) so the page loads fast

## Data observations
- Odd source values: HEROMOTOCO ROCE ~174% and OPM ~86%; ROCE/ROE anomalies are logged in output/ratio_edge_cases.log
- Market cap, P/E and prices are simulated; flagged in the sidebar

## Next
Sprint 5: NLP (analysis parser, auto pros/cons), cash-flow intelligence, PDF reports.