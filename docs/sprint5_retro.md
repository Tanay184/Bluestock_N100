# Sprint 5 Retrospective — Intelligence, Cash Flow & PDF Reports

## Delivered
- src/nlp/parser.py, src/nlp/pros_cons_generator.py; src/analytics/cashflow_intel.py
- src/reports/: common.py, tearsheet.py, sector_report.py, portfolio_report.py, build_reports.py
- output/: analysis_parsed.csv, parse_failures.csv, cross_validation.csv, pros_cons_generated.csv,
  cashflow_intelligence.xlsx, distress_alerts.csv, capital_allocation_summary.csv, pattern_changes.csv, skipped_tearsheets.csv
- reports/tearsheets (91 PDFs), reports/sector (10 PDFs), reports/portfolio/portfolio_summary.pdf (92 pages)
- 58 new tests (144 total), all passing; scripts/sprint5_check.py passes 8/8

## Results
- Analysis parser: 16 rows, 52 values parsed, 12 entries logged to parse_failures.csv. Cross-validation vs Ratio Engine: 23 OK, 1 DIVERGENT (for manual review), 28 not comparable (stock price CAGR, ROE)
- Pros/cons: 473 entries, 92/92 companies have >=1 pro and >=1 con; 58 sector/universe-relative fallback entries, of which 7 are at or below 60% confidence (kept so every company has a pro and a con)
- Cash flow intelligence: 92 companies, 13 distress signals, 26 deleveraging; capital_allocation complete (1,073 rows)
- Latest-year patterns: Shareholder Returns 40, Reinvestor 16, Mixed 14, Growth Funded by Debt 13, Liquidating Assets 7, Distress Signal 1, Pre-Revenue 1; 50 companies changed pattern in the latest year
- Reports: 91 tearsheets (all 2 pages, smallest 99 KB; JIOFIN skipped, only 2 years of data), 10 sector PDFs, portfolio summary 92 pages, full build about 40 s
- Visual review: tearsheets checked for TCS, HDFCBANK, TECHM, KOTAKBANK and others: no overflow or blank pages

## Decisions and deviations
- Cash flow logic lives in cashflow_intel.py (cashflow_kpis.py already existed from Sprint 2)
- Pro Rule 11 follows the rule text (profit CAGR above revenue CAGR) because the title and text on the board disagree
- Parser regex is the spec pattern plus an optional minus sign for negative growth
- Financials are exempt from margin, leverage and coverage rules (OPM, D/E, ICR, ROCE, net debt/EBITDA); D/E is also excluded from fallback entries for banks
- Confidence = 60 + 40 x (distance past threshold / scale); only scores above 60 are kept. Fallback entries use the company's best percentile versus sector or the Nifty 100
- Sector reports: 10 PDFs because the database has 10 sectors with companies (the spec lists 11; Conglomerates has no members)
- Market data (prices, market cap) is simulated and labelled as such in the reports

## Next
Sprint 6: clustering, REST API, full test suite, documentation and acceptance checklist.