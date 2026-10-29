"""Screener: 10 slider filters, 6 presets, live results and CSV export."""

import pandas as pd
import streamlit as st

from src.analytics.screener import condition, load_config
from src.dashboard.utils import db

CFG = load_config()
# key, label, metric, op, min, max, step, off (slider at 'off' = filter disabled)
SLIDERS = [
    ("roe_min", "ROE min (%)", "roe", ">=", -20.0, 80.0, 1.0, -20.0),
    ("de_max", "D/E max", "de", "<=", 0.0, 20.0, 0.5, 20.0),
    ("fcf_min", "FCF min (Cr)", "fcf", ">=", -20000.0, 60000.0, 500.0, -20000.0),
    (
        "rev_cagr_min",
        "Revenue CAGR 5yr min (%)",
        "rev_cagr_5yr",
        ">=",
        -10.0,
        40.0,
        1.0,
        -10.0,
    ),
    (
        "pat_cagr_min",
        "PAT CAGR 5yr min (%)",
        "pat_cagr_5yr",
        ">=",
        -10.0,
        60.0,
        1.0,
        -10.0,
    ),
    ("opm_min", "OPM min (%)", "opm", ">=", -10.0, 60.0, 1.0, -10.0),
    ("pe_max", "P/E max", "pe", "<=", 0.0, 150.0, 1.0, 150.0),
    ("pb_max", "P/B max", "pb", "<=", 0.0, 30.0, 0.5, 30.0),
    ("div_min", "Dividend yield min (%)", "div_yield", ">=", 0.0, 6.0, 0.1, 0.0),
    ("icr_min", "Interest coverage min (x)", "icr", ">=", 0.0, 50.0, 0.5, 0.0),
]
PRESETS = {
    "Quality": "quality_compounder",
    "Value": "value_pick",
    "Growth": "growth_accelerator",
    "Dividend": "dividend_champion",
    "Debt-Free": "debt_free_blue_chip",
    "Turnaround": "turnaround_watch",
}
SHOW = {
    "company_id": "Company ID",
    "company_name": "Company",
    "broad_sector": "Sector",
    "screen_score": "Score",
    "roe": "ROE %",
    "roce": "ROCE %",
    "de": "D/E",
    "fcf": "FCF (Cr)",
    "rev_cagr_5yr": "Rev CAGR 5yr %",
    "pat_cagr_5yr": "PAT CAGR 5yr %",
    "opm": "OPM %",
    "pe": "P/E",
    "pb": "P/B",
    "div_yield": "Div Yield %",
    "icr": "ICR",
}


def reset() -> None:
    """Switch all sliders off and clear preset-only conditions."""
    for s in SLIDERS:
        st.session_state[s[0]] = s[7]
    st.session_state["extras"] = []


def apply_preset(name: str) -> None:
    """Fill sliders from a preset; conditions without a slider are kept as extra filters."""
    reset()
    by_metric = {s[2]: s for s in SLIDERS}
    for f in CFG["presets"][name]["filters"]:
        s = by_metric.get(f["metric"])
        lower = f["op"] in (">", ">=")
        if s and lower == (s[3] == ">="):
            st.session_state[s[0]] = float(f["value"])
        else:
            st.session_state["extras"].append(f)


for s in SLIDERS:
    st.session_state.setdefault(s[0], s[7])
st.session_state.setdefault("extras", [])

st.title("Financial Screener")
st.caption("P/E, P/B and dividend yield use SIMULATED market data.")
cols = st.columns(len(PRESETS) + 1)
for col, (label, name) in zip(cols, PRESETS.items()):
    col.button(label, on_click=apply_preset, args=(name,), key=f"btn_{name}")
cols[-1].button("Reset", on_click=reset, key="btn_reset")

for key, label, _m, _op, lo, hi, step, _off in SLIDERS:
    st.sidebar.slider(label, min_value=lo, max_value=hi, step=step, key=key)

df = db.get_snapshot()
mask = pd.Series(True, index=df.index)
for key, _label, metric, op, _lo, _hi, _step, off in SLIDERS:
    value = st.session_state[key]
    if value == off:
        continue
    cond = condition(df, metric, op, value)
    if metric == "icr":
        cond = cond | (df["icr_label"] == "Debt Free")
    mask &= cond
for f in st.session_state["extras"]:
    mask &= condition(df, f["metric"], f["op"], f["value"])

out = (
    df[mask]
    .sort_values("screen_score", ascending=False)[list(SHOW)]
    .rename(columns=SHOW)
    .round(2)
)
st.subheader(f"{len(out)} companies match your filters")
if st.session_state["extras"]:
    extra = ", ".join(
        f"{f['metric']} {f['op']} {f['value']}" for f in st.session_state["extras"]
    )
    st.caption(f"Preset conditions also applied: {extra}")
if out.empty:
    st.info("No companies match. Loosen a filter or press Reset.")
st.dataframe(out.style.format(precision=2, na_rep="N/A"), hide_index=True)
st.download_button(
    "Download CSV",
    out.to_csv(index=False).encode("utf-8"),
    "screener_results.csv",
    "text/csv",
)
