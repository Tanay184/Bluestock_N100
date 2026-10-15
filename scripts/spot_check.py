"""Recompute ROE and 5yr revenue CAGR by hand for 3 companies and compare to the DB."""

import sqlite3

import pandas as pd

conn = sqlite3.connect("data/nifty100.db")
y, y0 = "2024-03", "2019-03"
rows = []
for t in ("TCS", "INFY", "HDFCBANK"):
    q = "SELECT * FROM {} WHERE company_id=?"
    p = pd.read_sql(q.format("profitandloss"), conn, params=(t,)).set_index("year")
    b = pd.read_sql(q.format("balancesheet"), conn, params=(t,)).set_index("year")
    d = pd.read_sql(q.format("financial_ratios"), conn, params=(t,)).set_index("year")
    roe = (
        p.at[y, "net_profit"] / (b.at[y, "equity_capital"] + b.at[y, "reserves"]) * 100
    )
    cg = ((p.at[y, "sales"] / p.at[y0, "sales"]) ** 0.2 - 1) * 100
    rows.append(
        {
            "company": t,
            "roe_manual": roe,
            "roe_db": d.at[y, "return_on_equity_pct"],
            "cagr_manual": cg,
            "cagr_db": d.at[y, "revenue_cagr_5yr"],
        }
    )
res = pd.DataFrame(rows)
res["roe_diff"] = (res["roe_manual"] - res["roe_db"]).abs()
res["cagr_diff"] = (res["cagr_manual"] - res["cagr_db"]).abs()
print(res.round(4).to_string(index=False))
demo = pd.read_sql(
    "SELECT * FROM financial_ratios WHERE year='2024-03' AND company_id IN ('TCS','INFY','HDFCBANK','RELIANCE','ITC')",
    conn,
)
demo.to_csv("output/sprint2_demo.csv", index=False)
print("\nDemo file written: output/sprint2_demo.csv", demo.shape)
