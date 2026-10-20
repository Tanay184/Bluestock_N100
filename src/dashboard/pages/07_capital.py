"""Capital allocation map: treemap by pattern plus a company list per pattern."""

import plotly.express as px
import streamlit as st

from src.dashboard.utils import db

st.title("Capital Allocation Map")
cap = db.get_capital().sort_values("year").groupby("company_id").tail(1)
st.caption(
    "Latest year per company; pattern comes from the signs of operating / investing / financing cash flow."
)

fig = px.treemap(
    cap.assign(companies=1),
    path=[px.Constant("Nifty 100"), "pattern_label", "company_name"],
    values="companies",
    color="pattern_label",
)
st.plotly_chart(fig)

counts = cap["pattern_label"].value_counts()
pattern = st.selectbox(
    "Show companies in pattern",
    counts.index.tolist(),
    format_func=lambda p: f"{p} ({counts[p]})",
)
rows = cap[cap["pattern_label"] == pattern][
    ["company_id", "company_name", "year", "cfo_sign", "cfi_sign", "cff_sign"]
]
rows.columns = ["Ticker", "Company", "Year", "CFO", "CFI", "CFF"]
st.dataframe(rows, hide_index=True)
