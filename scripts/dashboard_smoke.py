"""Day 27 QA: run every dashboard page via Streamlit AppTest; report errors and load times."""

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from streamlit.testing.v1 import AppTest

PAGES = ROOT / "src" / "dashboard" / "pages"
QUICK = {
    "TCS",
    "INFY",
    "HDFCBANK",
    "SBIN",
    "ITC",
    "HINDUNILVR",
    "RELIANCE",
    "ONGC",
    "SUNPHARMA",
    "CIPLA",
    "JIOFIN",
    "LICI",
    "ATGL",
    "ADANIGREEN",
}
TIMED = {"TCS", "INFY", "HDFCBANK", "ITC", "RELIANCE"}
failures: list[str] = []


def check(at: AppTest, page: str, name: str) -> None:
    """Record a failure if the last run raised."""
    if len(at.exception):
        failures.append(f"{page} [{name}]: {at.exception[0].value}")


def sweep(page: str, getter, picks=None) -> dict[str, float]:
    """Run a page once per selectbox option (or only options whose ticker is in picks)."""
    at = AppTest.from_file(str(PAGES / page), default_timeout=90)
    at.run()
    check(at, page, "default")
    opts = list(getter(at).options)
    times = {}
    for i, opt in enumerate(opts):
        if picks is not None and opt.split(" - ")[0] not in picks:
            continue
        getter(at).select_index(i)
        t0 = time.perf_counter()
        at.run()
        times[opt] = time.perf_counter() - t0
        check(at, page, opt)
    return times


def screener() -> int:
    """Presets, minimum and maximum slider values on the screener page."""
    page = "03_screener.py"
    at = AppTest.from_file(str(PAGES / page), default_timeout=90)
    at.run()
    check(at, page, "default")
    runs = 1
    for b in at.button:
        if str(b.key).startswith("btn_"):
            b.click()
            at.run()
            check(at, page, f"click {b.key}")
            runs += 1
    for label, pick in (("max", lambda s: s.max), ("min", lambda s: s.min)):
        for s in at.slider:
            s.set_value(pick(s))
        at.run()
        check(at, page, f"all sliders {label}")
        runs += 1
    return runs


def main() -> None:
    """Run all page sweeps and print a summary."""
    picks = None if "--all" in sys.argv else QUICK
    sel0 = lambda a: a.selectbox[0]
    runs = {
        "home": sweep("01_home.py", lambda a: a.sidebar.selectbox[0]),
        "profile": sweep("02_profile.py", sel0, picks),
        "peers": sweep("04_peers.py", sel0),
        "trends": sweep("05_trends.py", lambda a: a.selectbox(key="tr_sel"), picks),
        "sectors": sweep("06_sectors.py", sel0),
        "capital": sweep("07_capital.py", sel0),
        "reports": sweep("08_reports.py", lambda a: a.selectbox(key="rp_sel"), picks),
    }
    total = sum(len(v) for v in runs.values()) + screener()
    for name, t in runs.items():
        print(f"{name:8} runs={len(t):3}  slowest={max(t.values(), default=0):.2f}s")
    prof = {
        k.split(" - ")[0]: round(v, 2)
        for k, v in runs["profile"].items()
        if k.split(" - ")[0] in TIMED
    }
    print(
        "Profile load times (s):",
        prof,
        "| all under 3s:",
        all(v < 3 for v in prof.values()),
    )
    print(f"TOTAL page runs: {total} | failures: {len(failures)}")
    for f in failures:
        print(" -", f)
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
