"""Peer comparison: radar vs peer-group average and side-by-side KPI table."""

import numpy as np
import plotly.graph_objects as go
import streamlit as st

from src.analytics.peer import LABELS, RADAR, minmax
from src.dashboard.utils import db

TABLE = {
    "company_id": "Ticker",
    "company_name": "Company",
    "roe": "ROE %",
    "roce": "ROCE %",
    "npm": "NPM %",
    "opm": "OPM %",
    "de": "D/E",
    "fcf_margin": "FCF margin %",
    "rev_cagr_5yr": "Rev CAGR 5yr %",
    "pat_cagr_5yr": "PAT CAGR 5yr %",
    "eps_cagr_5yr": "EPS CAGR 5yr %",
    "pe": "P/E",
}

st.title("Peer Comparison")
group = st.selectbox("Peer group", db.get_peer_groups())
df = db.get_peers(group)
if df.empty:
    st.info("No companies found for this peer group.")
    st.stop()

names = dict(zip(df["company_id"], df["company_name"]))
company = st.selectbox(
    "Company", df["company_id"].tolist(), format_func=lambda c: f"{c} - {names[c]}"
)

scaled = df.set_index("company_id")[RADAR].apply(minmax)
theta = [LABELS[m] for m in RADAR]
fig = go.Figure()
for label, vals in (
    (company, scaled.loc[company]),
    ("Peer group average", scaled.mean()),
):
    r = vals.fillna(0).tolist()
    fig.add_trace(
        go.Scatterpolar(r=r + r[:1], theta=theta + theta[:1], fill="toself", name=label)
    )
fig.update_layout(
    polar={"radialaxis": {"range": [0, 100]}}, legend={"orientation": "h"}
)
st.plotly_chart(fig)
st.caption(
    "Each axis is scaled 0-100 within the peer group (100 = best; D/E is inverted)."
)

table = df.rename(columns=TABLE)
table.insert(0, "Benchmark", np.where(df["is_benchmark"] == 1, "★", ""))
table = table[["Benchmark", *TABLE.values()]].round(2)
st.subheader("Side-by-side KPIs (latest year)")
styled = table.style.apply(
    lambda r: (
        ["background-color: #fff3b0; color: black"] * len(r)
        if r["Benchmark"] == "★"
        else [""] * len(r)
    ),
    axis=1,
).format(precision=2, na_rep="N/A")
st.dataframe(styled, hide_index=True)
