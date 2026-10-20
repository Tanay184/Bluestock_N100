"""Trend analysis: up to 3 metrics over the last 10 years with YoY % labels."""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from src.dashboard.utils import db
from src.dashboard.utils.ui import company_picker

METRICS = {
    "Revenue (Cr)": "sales",
    "Net Profit (Cr)": "net_profit",
    "ROE %": "return_on_equity_pct",
    "ROCE %": "roce_pct",
    "Net Profit Margin %": "net_profit_margin_pct",
    "Operating Margin %": "operating_profit_margin_pct",
    "Debt / Equity": "debt_to_equity",
    "Free Cash Flow (Cr)": "free_cash_flow_cr",
    "EPS": "earnings_per_share",
}


def yoy_labels(s: pd.Series) -> list[str]:
    """YoY % change labels; blank when the prior value is zero, negative or missing."""
    prev = s.shift(1)
    pct = ((s / prev - 1) * 100).where(prev > 0)
    return [f"{p:+.0f}%" if pd.notna(p) else "" for p in pct]


st.title("Trend Analysis")
ticker = company_picker("tr")
picked = st.multiselect(
    "Metrics (overlay up to 3)",
    list(METRICS),
    default=["Revenue (Cr)", "ROE %"],
    max_selections=3,
)
if not picked:
    st.info("Pick at least one metric.")
    st.stop()

data = db.get_pl(ticker)[["year", "sales", "net_profit"]].merge(
    db.get_ratios(ticker), on="year", how="outer"
)
data = data.sort_values("year").tail(10)
if data.empty:
    st.info("No financial data available for this company.")
    st.stop()
for col in METRICS.values():
    if col not in data:
        data[col] = np.nan
if len(data) < 10:
    st.info(f"Only {len(data)} years of data are available for this company.")

fig = make_subplots(
    rows=len(picked),
    cols=1,
    shared_xaxes=True,
    vertical_spacing=0.1,
    subplot_titles=picked,
)
for i, name in enumerate(picked, 1):
    s = data[METRICS[name]].astype(float)
    fig.add_trace(
        go.Scatter(
            x=data["year"],
            y=s,
            mode="lines+markers+text",
            text=yoy_labels(s),
            textposition="top center",
        ),
        row=i,
        col=1,
    )
fig.update_layout(height=320 * len(picked), showlegend=False)
st.plotly_chart(fig)
st.caption(
    "Labels show year-on-year % change (blank when the prior value is zero or negative)."
)
