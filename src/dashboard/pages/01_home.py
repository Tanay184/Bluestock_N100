"""Home: market-wide KPI tiles, sector mix and top companies by quality score."""

import plotly.express as px
import streamlit as st

from src.dashboard.utils import db
from src.dashboard.utils.ui import fmt

st.title("Nifty 100 Analytics")
st.caption(
    "Fundamental analytics for 92 Nifty 100 companies. Prices, market caps and valuation multiples are SIMULATED."
)
year = st.sidebar.selectbox("Year", list(range(2024, 2018, -1)))

ratios = db.get_all_ratios()
ry = ratios[ratios["year"].str[:4] == str(year)]
mc = db.get_market_cap_all()
my = mc[mc["year"] == year]
roe = ry["return_on_equity_pct"].dropna()
roe_avg = roe.clip(roe.quantile(0.05), roe.quantile(0.95)).mean()

tiles = [
    ("Average ROE", fmt(roe_avg, "%")),
    ("Median P/E", fmt(my["pe_ratio"].median(), "x")),
    ("Median D/E", fmt(ry["debt_to_equity"].median(), nd=2)),
    ("Total Companies", fmt(ry["company_id"].nunique(), nd=0)),
    ("Median Rev CAGR 5yr", fmt(ry["revenue_cagr_5yr"].median(), "%")),
    ("Debt-Free Companies", fmt((ry["debt_to_equity"] == 0).sum(), nd=0)),
]
for col, (label, value) in zip(st.columns(6), tiles):
    st.caption(
        "Average ROE is capped at the 5th/95th percentile because a few companies have extreme ROE values."
    )
    col.metric(label, value)

left, right = st.columns(2)
sec = db.get_sectors().groupby("broad_sector").size().reset_index(name="companies")
left.plotly_chart(
    px.pie(
        sec,
        names="broad_sector",
        values="companies",
        hole=0.5,
        title="Companies by sector",
    )
)
names = db.get_companies()[["company_id", "company_name"]]
top = ry.merge(names, on="company_id").nlargest(5, "composite_quality_score")
top = top[["company_name", "broad_sector", "composite_quality_score"]]
top.columns = ["Company", "Sector", "Quality score"]
right.subheader(f"Top 5 by composite quality score ({year})")
right.dataframe(top, hide_index=True)
