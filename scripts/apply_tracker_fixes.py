"""Apply the Project Deliverables Tracker rules to the existing code (safe to run twice).

1. Financials are skipped when the D/E screener filter is applied (screener module, dashboard page, API).
2. Simulated market data is labelled SIMULATED in the dashboard, reports and valuation_summary.xlsx.
3. Makefile targets point at the real commands (make load / ratios / test / report / dashboard / api / clean).
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CONDITION = '''def condition(df: pd.DataFrame, metric: str, op: str, value: float) -> pd.Series:
    """Boolean mask for one filter; D/E upper limits are not applied to the Financials sector."""
    mask = OPS[op](df[metric], value)
    if metric in ("de", "debt_to_equity") and op in ("<", "<=") and "broad_sector" in df.columns:
        mask = mask | (df["broad_sector"] == "Financials")
    return mask


'''

MAKEFILE = """PY = python

load:
\t$(PY) -m src.etl.loader

ratios:
\t$(PY) -m src.analytics.run_ratios

analytics:
\t$(PY) -m src.analytics.screener
\t$(PY) -m src.analytics.peer
\t$(PY) -m src.analytics.valuation
\t$(PY) -m src.nlp.parser
\t$(PY) -m src.nlp.pros_cons_generator
\t$(PY) -m src.analytics.cashflow_intel
\t$(PY) -m src.analytics.clustering

test:
\t$(PY) -m pytest tests/ -q --html=reports/pytest_report.html --self-contained-html

report:
\t$(PY) -m src.reports.build_reports

dashboard:
\tstreamlit run src/dashboard/app.py

api:
\tuvicorn src.api.main:app --port 8000

clean:
\tpowershell -NoProfile -Command "Get-ChildItem -Recurse -Include __pycache__,.pytest_cache,.ruff_cache | Remove-Item -Recurse -Force"

.PHONY: load ratios analytics test report dashboard api clean
"""

results: list[tuple[str, str, str]] = []


def edit(
    rel: str,
    what: str,
    pattern: str,
    repl: str,
    marker: str | None = None,
    flags: int = 0,
    literal: bool = False,
) -> None:
    """Apply one regex (or literal) replacement and record APPLIED / ALREADY / NOT FOUND."""
    path = ROOT / rel
    if not path.exists():
        results.append(("MISSING FILE", rel, what))
        return
    text = path.read_text(encoding="utf-8")
    if marker and marker in text:
        results.append(("ALREADY", rel, what))
        return
    new, n = (
        (text.replace(pattern, repl), text.count(pattern))
        if literal
        else re.subn(pattern, repl, text, flags=flags)
    )
    if n == 0:
        results.append(("NOT FOUND", rel, what))
        return
    path.write_text(new, encoding="utf-8")
    results.append(("APPLIED", rel, what))


def main() -> None:
    """Run every edit and print a summary."""
    # 1. Financials skip for D/E filters
    edit(
        "src/analytics/screener.py",
        "add condition() helper",
        "def apply_filters(",
        CONDITION + "def apply_filters(",
        marker="def condition(",
        literal=True,
    )
    edit(
        "src/analytics/screener.py",
        "apply_filters uses condition()",
        r'mask &= OPS\[f\["op"\]\]\(df\[f\["metric"\]\], f\["value"\]\)',
        'mask &= condition(df, f["metric"], f["op"], f["value"])',
        marker='condition(df, f["metric"], f["op"]',
    )
    edit(
        "src/api/routers/screener.py",
        "API filter uses condition()",
        r'df = df\[df\[col\] >= value\] if op == ">=" else df\[df\[col\] <= value\]',
        "df = df[condition(df, col, op, value)]",
        marker="condition(df, col, op, value)",
    )
    edit(
        "src/api/routers/screener.py",
        "API import",
        r"(from src\.api\.deps import)",
        r"from src.analytics.screener import condition\n\1",
        marker="from src.analytics.screener import condition",
    )
    edit(
        "src/dashboard/pages/03_screener.py",
        "dashboard import",
        r"from src\.analytics\.screener import OPS, load_config",
        "from src.analytics.screener import condition, load_config",
        marker="import condition, load_config",
    )
    edit(
        "src/dashboard/pages/03_screener.py",
        "dashboard slider filter",
        r'cond = df\[metric\] >= value if op == ">=" else df\[metric\] <= value',
        "cond = condition(df, metric, op, value)",
        marker="cond = condition(df, metric, op, value)",
    )
    edit(
        "src/dashboard/pages/03_screener.py",
        "dashboard preset extras",
        r'mask &= OPS\[f\["op"\]\]\(df\[f\["metric"\]\], f\["value"\]\)',
        'mask &= condition(df, f["metric"], f["op"], f["value"])',
        marker='mask &= condition(df, f["metric"]',
    )
    edit(
        "tests/api/test_screener.py",
        "API test allows Financials above the D/E cap",
        r'r\["de"\] <= 1(?! or)',
        '(r["de"] <= 1 or r["broad_sector"] == "Financials")',
        marker='r["broad_sector"] == "Financials")',
    )
    edit(
        "src/reports/analyst_guide.py",
        "guide mentions the Financials rule",
        "Interest coverage treats debt-free companies as passing.",
        "Interest coverage treats debt-free companies as passing. The D/E maximum is not applied to Financials (banks and NBFCs).",
        marker="not applied to Financials",
        literal=True,
    )
    # 2. SIMULATED labels
    edit(
        "src/dashboard/app.py",
        "sidebar label",
        r'st\.sidebar\.caption\(\s*"[^"]*"\s*\)',
        'st.sidebar.caption("Stock prices, market cap and valuation multiples (P/E, P/B, EV/EBITDA, dividend yield) are SIMULATED data.")',
        marker="are SIMULATED data",
    )
    edit(
        "src/dashboard/pages/01_home.py",
        "home caption",
        "Prices and market caps are simulated.",
        "Prices, market caps and valuation multiples are SIMULATED.",
        marker="are SIMULATED.",
        literal=True,
    )
    edit(
        "src/dashboard/pages/06_sectors.py",
        "sector caption",
        "Market cap is simulated.",
        "Market cap is SIMULATED.",
        marker="Market cap is SIMULATED.",
        literal=True,
    )
    edit(
        "src/dashboard/pages/03_screener.py",
        "screener caption",
        r'(st\.title\("Financial Screener"\))',
        r'\1\nst.caption("P/E, P/B and dividend yield use SIMULATED market data.")',
        marker="SIMULATED market data",
    )
    for rel in ("tearsheet", "sector_report", "portfolio_report"):
        edit(
            f"src/reports/{rel}.py",
            "report footer",
            "Market data is simulated",
            "Market data is SIMULATED",
            marker="Market data is SIMULATED",
            literal=True,
        )
    edit(
        "src/reports/tearsheet.py",
        "tearsheet note",
        "market data is simulated.",
        "market data is SIMULATED.",
        marker="market data is SIMULATED.",
        literal=True,
    )
    edit(
        "src/analytics/valuation.py",
        "valuation_summary data_source column",
        r"^(\s*)val\.to_excel\(",
        r'\1val["data_source"] = "SIMULATED"\n\1val.to_excel(',
        marker='"data_source"',
        flags=re.MULTILINE,
    )
    # 3. Makefile
    (ROOT / "Makefile").write_text(MAKEFILE, encoding="utf-8", newline="\n")
    results.append(("APPLIED", "Makefile", "targets point at the real commands"))
    for status, rel, what in results:
        print(f"{status:12}{rel:45}{what}")
    bad = [r for r in results if r[0] in ("NOT FOUND", "MISSING FILE")]
    print(
        f"\n{len(results) - len(bad)}/{len(results)} edits in place"
        + (f" | {len(bad)} need a manual look (send this list)" if bad else "")
    )


if __name__ == "__main__":
    main()
