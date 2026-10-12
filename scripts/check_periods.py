import sqlite3

c = sqlite3.connect("data/nifty100.db")
for t in ("profitandloss", "balancesheet", "cashflow", "financial_ratios"):
    rows = c.execute(
        f"SELECT year, COUNT(*) FROM {t} WHERE year > '2024-03' GROUP BY year"
    ).fetchall()
    print(t, rows)
print(
    "BS 2024-09 rows with no P&L 2024-09:",
    c.execute(
        "SELECT COUNT(*) FROM balancesheet b WHERE b.year='2024-09' AND NOT EXISTS "
        "(SELECT 1 FROM profitandloss p WHERE p.company_id=b.company_id AND p.year=b.year)"
    ).fetchone()[0],
)
