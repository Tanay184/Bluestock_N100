# Sprint 1 Retrospective — Data Foundation

## Delivered
- nifty100.db (12 tables), load_audit.csv, validation_failures.csv
- src/etl/{normaliser,validator,loader}.py, db/schema.sql
- 43 unit tests (all passing), notebooks/exploratory_queries.sql (10 queries)

## Exit criteria
- companies = 92; PRAGMA foreign_key_check = 0 rows; critical_unresolved = 0 in all tables
- 88/92 companies have >=10 years of P&L (AC-02: >=90%)

## Deviations / findings
- Loaded rows are below spec estimates (P&L 1070 vs ~1276): spec counts raw rows incl.
  100 TTM rows, partial periods (9m, 15m, 2024.5), duplicates and orphan tickers; these are excluded by design.
- 8 tickers in statements are not in companies.xlsx (ULTRACEMCO, UNIONBANK, UNITDSPR, VBL, VEDL,
  WIPRO, ZOMATO, ZYDUSLIFE): rejected per DQ-03 and logged.
- cashflow.xlsx typo AGTL aliased to ATGL.
- SBIN has no balance sheet rows in source; DIVISLAB has no annual report links.
- Short-history companies (<10 yrs): JIOFIN (2), LICI (6), ATGL (7), ADANIGREEN (8).
- Balance sheet contains 2024-09 period rows not present in P&L/CF; handle in Sprint 2 joins.

## Next
Sprint 2: Financial Ratio Engine (ratios, CAGR, cash flow KPIs, financial_ratios table).- Balance sheet has 83 rows at 2024-09 (82 without a matching P&L/CF period; only SIEMENS has a Sept year-end). Kept in DB as source data; the ratio engine joins on (company_id, year) so unmatched periods are excluded.
