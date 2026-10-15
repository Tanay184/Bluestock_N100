# Sprint 2 Retrospective — Financial Ratio Engine

## Delivered
- src/analytics: ratios.py, cagr.py, cashflow_kpis.py, run_ratios.py
- financial_ratios table (1,073 rows, 92 companies, 30+ columns incl. 14 required KPIs, CAGR 3/5/10yr + flags, composite score)
- output/capital_allocation.csv, output/ratio_edge_cases.log, output/sector_roce_notes.csv
- tests/kpi: 42 new tests (85 total), all passing

## Exit criteria
- Rows: 1,073 vs target 1,100 — deviation: only ~1,070 true annual P&L periods exist after excluding TTM/partial periods (Sprint 1 finding)
- No all-null KPI columns; 0 test failures
- Spot-check (TCS, INFY, HDFCBANK, FY2024-03): ROE and 5yr revenue CAGR match manual calc, diff 0.0
- Screener preview (ROE>15, D/E<1, FY2024-03): 37 companies (target 15-50)

## Formula decisions
- D/E = 0 for debt-free; None if equity <= 0. High-leverage flag (D/E>5) suppressed for Financials.
- ICR None when interest = 0, label "Debt Free"; warning flag when ICR < 1.5.
- CAGR flags: TURNAROUND, DECLINE_TO_LOSS, BOTH_NEGATIVE, ZERO_BASE, INSUFFICIENT.
- Balance-sheet-only periods (2024-09) excluded from ratios (82 rows).
- Composite score: 0.30 ROE + 0.25 FCF margin + 0.25 ROCE + 0.20 D/E, winsorised P10/P90 per year; Financials D/E score fixed at 50.
- Capital allocation: 8 sign patterns mapped to labels in cashflow_kpis.PATTERNS.

## Edge-case log summary
OPM_MISMATCH 216, CAGR_TURNAROUND 145, CAGR_DECLINE_TO_LOSS 129, NON_ANNUAL_PERIOD 82,
ROCE_ANOMALY 37, CAGR_BOTH_NEGATIVE 36, DEBT_FREE_ICR 31, CAGR_ZERO_BASE 25, ROE_ANOMALY 20, DIV_ZERO 1.
ROE anomalies (20): 3 data source issue, 7 version difference, 10 formula discrepancy.
ROCE anomalies (37): 1 data source issue, 7 version difference, 29 formula discrepancy.
The categories are heuristic. The "formula discrepancy" bucket mainly reflects that the
pre-computed roce_percentage in companies.xlsx uses an undocumented definition. The engine
follows the spec formula (EBIT / (equity + reserves + borrowings)); the source value is kept
for display only (e.g. TCS source ROE 0.52 is a data source issue).
(e.g. TCS source ROE 0.52 is a data source issue; engine value used for analytics).

## Next
Sprint 3: screener (6 presets, YAML config), ranking engine, peer percentiles, radar charts.