"""Data-quality validator implementing DQ-01 .. DQ-16."""

import logging

import pandas as pd

from src.etl.normaliser import PARSE_ERROR

logger = logging.getLogger(__name__)
COLS = ["rule_id", "table", "company_id", "year", "field", "issue", "severity"]
TS = ["profitandloss", "balancesheet", "cashflow"]
YEAR_TABLES = TS + ["financial_ratios"]


def _rows(rule, table, df, field, issue, severity) -> list[dict]:
    """Build failure records from the offending rows of df."""
    if df.empty:
        return []
    cid = df["company_id"] if "company_id" in df else df["id"]
    yr = df["year"] if "year" in df else [None] * len(df)
    return [
        {
            "rule_id": rule,
            "table": table,
            "company_id": c,
            "year": y,
            "field": field,
            "issue": issue,
            "severity": severity,
        }
        for c, y in zip(cid, yr)
    ]


def _bad_urls(docs: pd.DataFrame) -> pd.DataFrame:
    """Return document rows whose URL does not answer HTTP 200."""
    from concurrent.futures import ThreadPoolExecutor

    import requests

    def ok(u):
        try:
            return requests.head(u, timeout=5, allow_redirects=True).status_code == 200
        except requests.RequestException:
            return False

    with ThreadPoolExecutor(16) as ex:
        res = list(
            ex.map(lambda u: bool(u) and ok(u), docs["Annual_Report"].fillna(""))
        )
    return docs[[not r for r in res]]


def validate(t: dict[str, pd.DataFrame], check_urls: bool = False) -> pd.DataFrame:
    """Run all 16 DQ rules on normalised tables; return failures DataFrame."""
    f: list[dict] = []
    comp, pl, bs, cf = (
        t["companies"],
        t["profitandloss"],
        t["balancesheet"],
        t["cashflow"],
    )
    ids = set(comp["id"].dropna())

    f += _rows(
        "DQ-01",
        "companies",
        comp[comp["id"].duplicated(keep=False)],
        "id",
        "duplicate ticker",
        "CRITICAL",
    )
    for n in TS:
        d = t[n]
        f += _rows(
            "DQ-02",
            n,
            d[d.duplicated(["company_id", "year"], keep="last")],
            "company_id,year",
            "duplicate key",
            "CRITICAL",
        )
    for n, d in t.items():
        if n != "companies":
            f += _rows(
                "DQ-03",
                n,
                d[~d["company_id"].isin(ids)],
                "company_id",
                "orphan FK",
                "CRITICAL",
            )
    gap = (bs.total_assets - bs.total_liabilities).abs()
    f += _rows(
        "DQ-04",
        "balancesheet",
        bs[(bs.total_assets > 0) & (gap / bs.total_assets >= 0.01)],
        "total_assets",
        "BS imbalance >=1%",
        "WARNING",
    )
    opm = pl.operating_profit / pl.sales * 100
    f += _rows(
        "DQ-05",
        "profitandloss",
        pl[(pl.sales > 0) & ((pl.opm_percentage - opm).abs() >= 1.0)],
        "opm_percentage",
        "OPM differs from computed >=1",
        "WARNING",
    )
    banks = set(
        t["sectors"].loc[t["sectors"].broad_sector == "Financials", "company_id"]
    )
    f += _rows(
        "DQ-06",
        "profitandloss",
        pl[(pl.sales <= 0) & ~pl.company_id.isin(banks)],
        "sales",
        "sales <= 0",
        "WARNING",
    )
    for n in YEAR_TABLES:
        f += _rows(
            "DQ-07",
            n,
            t[n][t[n]["year"] == PARSE_ERROR],
            "year",
            "unparseable year",
            "CRITICAL",
        )
    for n, d in t.items():
        col = "id" if n == "companies" else "company_id"
        ln = d[col].astype(str).str.len()
        f += _rows(
            "DQ-08",
            n,
            d[d[col].isna() | (ln < 2) | (ln > 12)],
            col,
            "bad ticker",
            "CRITICAL",
        )
    calc = cf.operating_activity + cf.investing_activity + cf.financing_activity
    f += _rows(
        "DQ-09",
        "cashflow",
        cf[(cf.net_cash_flow - calc).abs() > 10],
        "net_cash_flow",
        "mismatch > 10 Cr",
        "WARNING",
    )
    f += _rows(
        "DQ-10",
        "balancesheet",
        bs[bs.fixed_assets < 0],
        "fixed_assets",
        "negative",
        "WARNING",
    )
    f += _rows(
        "DQ-11",
        "profitandloss",
        pl[(pl.tax_percentage < 0) | (pl.tax_percentage > 60)],
        "tax_percentage",
        "outside 0-60",
        "WARNING",
    )
    f += _rows(
        "DQ-12",
        "profitandloss",
        pl[pl.dividend_payout > 200],
        "dividend_payout",
        ">200%",
        "WARNING",
    )
    if check_urls:
        f += _rows(
            "DQ-13",
            "documents",
            _bad_urls(t["documents"]),
            "Annual_Report",
            "URL not 200",
            "WARNING",
        )
    f += _rows(
        "DQ-14",
        "profitandloss",
        pl[(pl.net_profit > 0) & (pl.eps <= 0)],
        "eps",
        "eps<=0 with profit>0",
        "WARNING",
    )
    n15 = int((gap > 0).sum())
    f.append(
        {
            "rule_id": "DQ-15",
            "table": "balancesheet",
            "company_id": "ALL",
            "year": None,
            "field": "total_assets",
            "issue": f"{n15} rows not strictly balanced",
            "severity": "INFO",
        }
    )
    for n in TS:
        cnt = (
            t[n]
            .groupby("company_id")["year"]
            .nunique()
            .reindex(sorted(ids), fill_value=0)
        )
        for c in cnt[cnt < 5].index:
            f.append(
                {
                    "rule_id": "DQ-16",
                    "table": n,
                    "company_id": c,
                    "year": None,
                    "field": "year",
                    "issue": f"only {cnt[c]} years",
                    "severity": "WARNING",
                }
            )
    out = pd.DataFrame(f, columns=COLS)
    logger.info("validation: %d failures", len(out))
    return out
