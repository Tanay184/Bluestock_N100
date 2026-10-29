"""Sector analysis: revenue vs ROE bubble chart and sector median KPIs."""

import pandas as pd
import plotly.express as px
import streamlit as st

from src.dashboard.utils import db

KPIS = {
    "roe": "ROE %",
    "roce": "ROCE %",
    "npm": "Net margin %",
    "opm": "Operating margin %",
    "rev_cagr_5yr": "Revenue CAGR 5yr %",
    "pat_cagr_5yr": "PAT CAGR 5yr %",
}

st.title("Sector Analysis")
snap = db.get_snapshot()
sector = st.selectbox("Sector", sorted(snap["broad_sector"].dropna().unique()))
sub = snap[snap["broad_sector"] == sector]

bub = sub.dropna(subset=["sales", "roe", "market_cap_crore"])
bub = bub[(bub["sales"] > 0) & (bub["market_cap_crore"] > 0)]
if bub.empty:
    st.info("Not enough data to draw the bubble chart for this sector.")
else:
    fig = px.scatter(
        bub,
        x="sales",
        y="roe",
        size="market_cap_crore",
        color="sub_sector",
        hover_name="company_name",
        log_x=True,
        size_max=55,
        title=f"{sector}: revenue vs ROE (bubble = market cap)",
        labels={
            "sales": "Revenue (Cr, log scale)",
            "roe": "ROE %",
            "sub_sector": "Sub-sector",
        },
    )
    st.plotly_chart(fig)
    st.caption(
        f"{len(bub)} of {len(sub)} companies shown (need revenue, ROE and market cap). Market cap is SIMULATED."
    )

med = pd.DataFrame(
    {
        "KPI": list(KPIS.values()),
        sector: sub[list(KPIS)].median().values,
        "Nifty 100": snap[list(KPIS)].median().values,
    }
)
fig2 = px.bar(
    med.melt("KPI", var_name="Group", value_name="Median"),
    x="KPI",
    y="Median",
    color="Group",
    barmode="group",
    title=f"Median KPIs: {sector} vs Nifty 100",
)
st.plotly_chart(fig2)
