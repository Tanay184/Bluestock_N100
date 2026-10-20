import streamlit as st

from src.dashboard.utils import db

"""Small UI helpers for the dashboard."""

import math


def fmt(value, suffix: str = "", nd: int = 1) -> str:
    """Format a number for display; 'N/A' for None/NaN/non-numeric."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return "N/A"
    return "N/A" if math.isnan(v) else f"{v:,.{nd}f}{suffix}"


def company_picker(key: str) -> str:
    """Search box plus dropdown; returns the selected ticker (stops the page if nothing matches)."""
    comp = db.get_companies()
    labels = (comp["company_id"] + " - " + comp["company_name"]).tolist()
    query = st.text_input(
        "Search by company name or ticker",
        key=f"{key}_q",
        placeholder="e.g. TCS or Infosys",
    )
    hits = [x for x in labels if query.lower() in x.lower()] if query else labels
    if not hits:
        st.warning("Ticker not found - please try another")
        st.stop()
    idx = next((i for i, x in enumerate(hits) if x.startswith("TCS - ")), 0)
    return st.selectbox("Select company", hits, index=idx, key=f"{key}_sel").split(
        " - ", 1
    )[0]
