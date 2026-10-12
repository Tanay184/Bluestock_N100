"""Day 6: year coverage for 5 random companies plus short-history companies."""

import random
import sqlite3

import pandas as pd

conn = sqlite3.connect("data/nifty100.db")
ids = [r[0] for r in conn.execute("SELECT id FROM companies")]
random.seed(7)
for c in random.sample(ids, 5):
    print("\n==", c)
    for t in ("profitandloss", "balancesheet", "cashflow", "financial_ratios"):
        y = [
            r[0]
            for r in conn.execute(
                f"SELECT year FROM {t} WHERE company_id=? ORDER BY year", (c,)
            )
        ]
        print(f"{t:17} {len(y):2} yrs  {y[0] if y else '-'} -> {y[-1] if y else '-'}")
few = pd.read_sql(
    "SELECT company_id, COUNT(*) yrs FROM profitandloss GROUP BY company_id HAVING yrs < 5",
    conn,
)
print("\nCompanies with <5 P&L years:\n", few.to_string(index=False))
