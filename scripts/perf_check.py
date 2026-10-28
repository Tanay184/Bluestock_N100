"""Day 43: load test, dashboard timing and end-to-end check. Writes output/perf_notes.md and output/perf_results.json.

Stop any running dashboard/API first (ports 8000 and 8501 must be free).
    python scripts/perf_check.py
    python scripts/perf_check.py --skip-dashboard     # API checks only
"""

import json
import os
import re
import socket
import subprocess
import sys
import threading
import time
from datetime import UTC, datetime
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

API = "http://127.0.0.1:8000"  # 127.0.0.1, not localhost: on Windows localhost can add ~2 s per new connection (IPv6 fallback)
DASH = "http://127.0.0.1:8501"
PROFILE_TICKERS = ["TCS", "INFY", "HDFCBANK", "ITC", "RELIANCE"]
OUT = ROOT / "output"


def port_free(port: int) -> bool:
    """True if nothing is listening on the local port."""
    with socket.socket() as s:
        return s.connect_ex(("127.0.0.1", port)) != 0


def start(cmd: list[str]) -> subprocess.Popen:
    """Start a server process in the project root without a console window."""
    flags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    return subprocess.Popen(
        cmd,
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=flags,
    )


def stop(proc: subprocess.Popen) -> None:
    """Terminate a server process and its children."""
    if proc.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
            capture_output=True,
            check=False,
        )
    else:
        proc.terminate()


def wait_for(url: str, expect: str | None = None, seconds: int = 60) -> bool:
    """Poll a URL until it answers 200 (and contains the expected text)."""
    end = time.time() + seconds
    while time.time() < end:
        try:
            r = requests.get(url, timeout=3)
            if r.status_code == 200 and (expect is None or expect in r.text):
                return True
        except requests.RequestException:
            pass
        time.sleep(1)
    return False


def load_test(n: int = 10) -> dict:
    """Fire n concurrent screener requests with threads."""
    times, codes = [], []
    lock = threading.Lock()

    def hit() -> None:
        t0 = time.perf_counter()
        try:
            code = requests.get(
                f"{API}/api/v1/screener",
                params={"min_roe": 10, "max_de": 2},
                timeout=30,
            ).status_code
        except requests.RequestException:
            code = 0
        with lock:
            times.append(time.perf_counter() - t0)
            codes.append(code)

    threads = [threading.Thread(target=hit) for _ in range(n)]
    t0 = time.perf_counter()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    total = time.perf_counter() - t0
    return {
        "calls": n,
        "ok": codes.count(200),
        "total_s": round(total, 2),
        "slowest_s": round(max(times), 2),
        "passed": codes.count(200) == n and total <= 10,
    }


def endpoint_times() -> list[dict]:
    """Time one request to each of the 16 endpoints."""
    base = f"{API}/api/v1"
    group = "IT_Services"
    paths = [
        "/health",
        "/companies",
        "/companies/TCS",
        "/companies/TCS/pl",
        "/companies/TCS/bs",
        "/companies/TCS/cashflow",
        "/companies/TCS/ratios",
        "/companies/TCS/tearsheet",
        "/screener?min_roe=15",
        "/sectors",
        "/sectors/IT/companies",
        f"/peers/{group}",
        "/companies/TCS/peers/compare",
        "/market-cap/TCS",
        "/portfolio/stats",
        "/companies/TCS/documents",
    ]
    out = []
    for path in paths:
        t0 = time.perf_counter()
        try:
            code = requests.get(base + path, timeout=30).status_code
        except requests.RequestException:
            code = 0
        out.append(
            {
                "path": path,
                "status": code,
                "ms": round((time.perf_counter() - t0) * 1000, 1),
            }
        )
    return out


def dashboard_checks() -> dict:
    """Company Profile load time for 5 tickers and dashboard-versus-API screener comparison (Streamlit AppTest)."""
    from streamlit.testing.v1 import AppTest

    pages = ROOT / "src" / "dashboard" / "pages"
    at = AppTest.from_file(str(pages / "02_profile.py"), default_timeout=90)
    at.run()
    options = list(at.selectbox[0].options)
    times = {}
    for t in PROFILE_TICKERS:
        idx = next((i for i, o in enumerate(options) if o.startswith(f"{t} - ")), None)
        if idx is None:
            continue
        at.selectbox[0].select_index(idx)
        t0 = time.perf_counter()
        at.run()
        times[t] = round(time.perf_counter() - t0, 2)
    scr = AppTest.from_file(str(pages / "03_screener.py"), default_timeout=90)
    scr.run()
    scr.slider(key="roe_min").set_value(15.0)
    scr.slider(key="de_max").set_value(1.0)
    scr.run()
    text = scr.subheader[0].value
    m = re.match(r"(\d+) compan", text)
    dash_count = int(m.group(1)) if m else -1
    api_count = len(
        requests.get(
            f"{API}/api/v1/screener", params={"min_roe": 15, "max_de": 1}, timeout=30
        ).json()
    )
    return {
        "profile_load_s": times,
        "profile_passed": bool(times) and all(v < 3 for v in times.values()),
        "dashboard_screener_count": dash_count,
        "api_screener_count": api_count,
        "screener_match": dash_count == api_count,
    }


def main() -> None:
    """Run all checks, stop the servers and write the notes."""
    skip_dash = "--skip-dashboard" in sys.argv
    busy = [
        p for p in (8000, 8501) if not port_free(p) and not (skip_dash and p == 8501)
    ]
    if busy:
        sys.exit(
            f"Port(s) {busy} already in use: stop the running dashboard/API (Ctrl+C) and run this again."
        )
    results: dict = {"run_at": datetime.now(UTC).isoformat(timespec="seconds")}
    procs = [
        start([sys.executable, "-m", "uvicorn", "src.api.main:app", "--port", "8000"])
    ]
    if not skip_dash:
        procs.append(
            start(
                [
                    sys.executable,
                    "-m",
                    "streamlit",
                    "run",
                    "src/dashboard/app.py",
                    "--server.port",
                    "8501",
                    "--server.headless",
                    "true",
                ]
            )
        )
    try:
        results["api_up"] = wait_for(f"{API}/api/v1/health", '"status":"ok"')
        results["dashboard_up"] = (
            None if skip_dash else wait_for(f"{DASH}/_stcore/health", "ok")
        )
        if results["api_up"]:
            results["load_test"] = load_test()
            results["endpoints"] = endpoint_times()
            if not skip_dash and results["dashboard_up"]:
                try:
                    results["dashboard"] = dashboard_checks()
                except Exception as exc:  # noqa: BLE001
                    results["dashboard"] = {"error": f"{type(exc).__name__}: {exc}"}
        if not skip_dash:
            results["both_running"] = bool(
                results["api_up"] and results["dashboard_up"]
            )
    finally:
        for p in procs:
            stop(p)
    write_notes(results)
    OUT.mkdir(exist_ok=True)
    (OUT / "perf_results.json").write_text(
        json.dumps(results, indent=2), encoding="utf-8"
    )
    print(json.dumps({k: v for k, v in results.items() if k != "endpoints"}, indent=2))
    print(
        "slowest endpoints (ms):",
        sorted(
            ((e["ms"], e["path"]) for e in results.get("endpoints", [])), reverse=True
        )[:3],
    )
    print("wrote output/perf_notes.md")


def write_notes(r: dict) -> None:
    """Write output/perf_notes.md from the measurements."""
    lines = ["# Performance notes", "", f"Run at {r['run_at']} (UTC).", ""]
    lt = r.get("load_test")
    if lt:
        lines += [
            "## Load test: 10 concurrent screener calls",
            "",
            f"- {lt['ok']}/{lt['calls']} succeeded; all finished in {lt['total_s']} s (slowest {lt['slowest_s']} s). Target 10 s: **{'PASS' if lt['passed'] else 'FAIL'}**",
            "",
        ]
    ep = r.get("endpoints")
    if ep:
        slow = sorted(ep, key=lambda e: e["ms"], reverse=True)
        lines += (
            [
                "## API response times (one request each, cold cache for the first screener call)",
                "",
                "| Endpoint | Status | ms |",
                "|---|---|---|",
            ]
            + [f"| {e['path']} | {e['status']} | {e['ms']} |" for e in slow]
            + [""]
        )
    d = r.get("dashboard")
    if d and "error" in d:
        lines += ["## Dashboard", "", f"- Check could not run: {d['error']}", ""]
    elif d:
        lines += [
            "## Dashboard",
            "",
            f"- Company Profile load time (server-side): {d['profile_load_s']}. Target under 3 s each: **{'PASS' if d['profile_passed'] else 'FAIL'}**",
            f"- Screener ROE >= 15 and D/E <= 1: dashboard {d['dashboard_screener_count']} companies, API {d['api_screener_count']}: **{'MATCH' if d['screener_match'] else 'MISMATCH'}**",
            "",
        ]
    lines += [
        "## End to end",
        "",
        f"- API on port 8000 up: {r.get('api_up')}; dashboard on port 8501 up: {r.get('dashboard_up')}; both at the same time: {r.get('both_running')}",
        "",
        "## Bottlenecks and optimisation",
        "",
        "- The screener and sector endpoints build a metric snapshot from several tables; it is cached in memory until the database file changes, so only the first call is slow.",
        "- Indexes on company_id and year (and peer group) are created at API start-up (CREATE INDEX IF NOT EXISTS), which keeps per-company queries in the low milliseconds.",
        "- Timings use 127.0.0.1: on Windows the name localhost can add about 2 seconds to every new connection (IPv6 fallback), which would otherwise hide the real response times.",
        "- Live annual-report link validation (documents?validate=true) depends on the network and is off by default.",
        "- The dashboard caches every query for 10 minutes (st.cache_data), so repeat visits are near-instant.",
        "",
    ]
    OUT.mkdir(exist_ok=True)
    (OUT / "perf_notes.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
