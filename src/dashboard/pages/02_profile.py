"""Company profile: card, KPI tiles, 10-year charts and pros/cons."""

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from src.dashboard.utils import db
from src.dashboard.utils.ui import fmt

st.title("Company Profile")
comp = db.get_companies()
comp["label"] = comp["company_id"] + " - " + comp["company_name"]
query = st.text_input(
    "Search by company name or ticker", placeholder="e.g. TCS or Infosys"
)
hits = (
    comp[comp["label"].str.contains(query, case=False, regex=False)] if query else comp
)
if hits.empty:
    st.warning("Ticker not found - please try another")
    st.stop()

ids = hits["company_id"].tolist()
default = ids.index("TCS") if (not query and "TCS" in ids) else 0
choice = st.selectbox("Select company", hits["label"].tolist(), index=default)
row = hits[hits["label"] == choice].iloc[0]
ticker = row["company_id"]

st.subheader(row["company_name"])
st.caption(f"{ticker} | {row['broad_sector']} | {row['sub_sector']}")
about = row["about_company"]
st.write(about if isinstance(about, str) else "No description available.")

ratios, pl = db.get_ratios(ticker), db.get_pl(ticker)
if ratios.empty and pl.empty:
    st.info("No financial data available for this company.")
    st.stop()

if not ratios.empty:
    last = ratios.iloc[-1]
    st.caption(f"Latest financial year in data: {last['year']}")
    tiles = [
        ("ROE", fmt(last["return_on_equity_pct"], "%")),
        ("ROCE", fmt(last["roce_pct"], "%")),
        ("Net Profit Margin", fmt(last["net_profit_margin_pct"], "%")),
        ("Debt / Equity", fmt(last["debt_to_equity"], nd=2)),
        ("Revenue CAGR 5yr", fmt(last["revenue_cagr_5yr"], "%")),
        ("Free Cash Flow (Cr)", fmt(last["free_cash_flow_cr"], nd=0)),
    ]
    for col, (label, value) in zip(st.columns(6), tiles):
        col.metric(label, value)
    if len(ratios) < 10:
        st.info(f"Only {len(ratios)} years of data are available for this company.")

c1, c2 = st.columns(2)
if not pl.empty:
    p = pl.tail(10)
    fig = px.bar(
        p,
        x="year",
        y=["sales", "net_profit"],
        barmode="group",
        title="Revenue and Net Profit (Cr)",
    )
    c1.plotly_chart(fig)
if not ratios.empty:
    r10 = ratios.tail(10)
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Scatter(x=r10["year"], y=r10["return_on_equity_pct"], name="ROE %"),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(x=r10["year"], y=r10["roce_pct"], name="ROCE %"), secondary_y=True
    )
    fig.update_yaxes(title_text="ROE %", secondary_y=False)
    fig.update_yaxes(title_text="ROCE %", secondary_y=True)
    fig.update_layout(title="ROE and ROCE")
    c2.plotly_chart(fig)

st.subheader("Pros and cons")
pc = db.get_pros_cons(ticker)
if pc.empty:
    st.caption("No pros/cons on file for this company yet.")
else:
    pcol, ccol = st.columns(2)
    for text in pc["pros"].dropna():
        pcol.markdown(f"✅ {text}")
    for text in pc["cons"].dropna():
        ccol.markdown(f"❌ {text}")
