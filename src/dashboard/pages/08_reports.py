"""Annual reports: per-year BSE PDF links with an optional availability check."""

from concurrent.futures import ThreadPoolExecutor

import requests
import streamlit as st

from src.dashboard.utils import db
from src.dashboard.utils.ui import company_picker


@st.cache_data(ttl=3600)
def check_urls(urls: tuple[str, ...]) -> dict[str, bool]:
    """HEAD-request each URL; True when it answers HTTP 200."""

    def ok(u: str) -> bool:
        try:
            return requests.head(u, timeout=6, allow_redirects=True).status_code == 200
        except requests.RequestException:
            return False

    with ThreadPoolExecutor(8) as ex:
        return dict(zip(urls, ex.map(ok, urls)))


st.title("Annual Reports")
ticker = company_picker("rp")
docs = db.get_documents(ticker)
if docs.empty:
    st.info("No annual reports on file for this company.")
    st.stop()

st.caption(
    f"{len(docs)} reports on file ({docs['year'].min()} to {docs['year'].max()})."
)
verify = st.checkbox("Check which links still work (slower)", key="rp_check")
results = check_urls(tuple(docs["Annual_Report"].dropna())) if verify else {}


def status(url) -> str:
    """Badge text for one report link."""
    if not isinstance(url, str) or not url:
        return "🔴 Report unavailable"
    if not verify:
        return "Not checked"
    return "✅ Available" if results.get(url) else "🔴 Report unavailable"


docs["Status"] = docs["Annual_Report"].map(status)
docs = docs.rename(columns={"year": "Year", "Annual_Report": "Annual report"})
st.dataframe(
    docs,
    hide_index=True,
    column_config={
        "Annual report": st.column_config.LinkColumn(
            "Annual report", display_text="Open PDF"
        )
    },
)
