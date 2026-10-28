"""One unit test per data-quality rule: craft a violation and check rule_id and severity."""

import pandas as pd

from src.etl.normaliser import NON_ANNUAL, PARSE_ERROR
from src.etl.validator import validate

YEARS = [f"{y}-03" for y in range(2019, 2025)]
COMPANIES = ("AAA", "BBB")


def _frame(**cols) -> pd.DataFrame:
    rows = [{"company_id": c, "year": y, **cols} for c in COMPANIES for y in YEARS]
    return pd.DataFrame(rows)


def clean_tables() -> dict[str, pd.DataFrame]:
    """Two companies with six clean years in every statement table."""
    return {
        "companies": pd.DataFrame(
            {"id": list(COMPANIES), "company_name": ["A Ltd", "B Ltd"]}
        ),
        "sectors": pd.DataFrame(
            {"company_id": list(COMPANIES), "broad_sector": ["Industrials"] * 2}
        ),
        "profitandloss": _frame(
            sales=1000.0,
            operating_profit=200.0,
            opm_percentage=20.0,
            tax_percentage=25.0,
            dividend_payout=30.0,
            net_profit=100.0,
            eps=5.0,
        ),
        "balancesheet": _frame(
            total_assets=1000.0, total_liabilities=1000.0, fixed_assets=300.0
        ),
        "cashflow": _frame(
            operating_activity=100.0,
            investing_activity=-50.0,
            financing_activity=-30.0,
            net_cash_flow=20.0,
        ),
        "financial_ratios": _frame(),
    }


def found(t: dict, rule_id: str, severity: str) -> bool:
    """True if validate() reports the rule with the given severity."""
    res = validate(t)
    return bool(((res["rule_id"] == rule_id) & (res["severity"] == severity)).any())


def test_baseline_has_no_failures_except_info():
    res = validate(clean_tables())
    assert set(res.loc[res["rule_id"] != "DQ-15", "rule_id"]) == set()


def test_dq01_duplicate_company_id():
    t = clean_tables()
    t["companies"] = pd.concat(
        [t["companies"], t["companies"].iloc[[0]]], ignore_index=True
    )
    assert found(t, "DQ-01", "CRITICAL")


def test_dq02_duplicate_company_year():
    t = clean_tables()
    t["profitandloss"] = pd.concat(
        [t["profitandloss"], t["profitandloss"].iloc[[0]]], ignore_index=True
    )
    assert found(t, "DQ-02", "CRITICAL")


def test_dq03_orphan_company_id():
    t = clean_tables()
    orphan = t["cashflow"].iloc[[0]].assign(company_id="ZZZ")
    t["cashflow"] = pd.concat([t["cashflow"], orphan], ignore_index=True)
    assert found(t, "DQ-03", "CRITICAL")


def test_dq04_balance_sheet_imbalance():
    t = clean_tables()
    t["balancesheet"].loc[0, "total_liabilities"] = 1100.0
    assert found(t, "DQ-04", "WARNING")


def test_dq05_opm_mismatch():
    t = clean_tables()
    t["profitandloss"].loc[0, "opm_percentage"] = 50.0
    assert found(t, "DQ-05", "WARNING")


def test_dq06_non_positive_sales():
    t = clean_tables()
    t["profitandloss"].loc[0, "sales"] = 0.0
    assert found(t, "DQ-06", "WARNING")


def test_dq07_unparseable_and_non_annual_year():
    t = clean_tables()
    t["profitandloss"].loc[0, "year"] = PARSE_ERROR
    assert found(t, "DQ-07", "CRITICAL")
    t2 = clean_tables()
    t2["cashflow"].loc[0, "year"] = NON_ANNUAL
    assert found(t2, "DQ-07", "WARNING")


def test_dq08_bad_ticker_length():
    t = clean_tables()
    t["companies"] = pd.concat(
        [t["companies"], pd.DataFrame({"id": ["A"], "company_name": ["Short"]})],
        ignore_index=True,
    )
    assert found(t, "DQ-08", "CRITICAL")


def test_dq09_net_cash_flow_mismatch():
    t = clean_tables()
    t["cashflow"].loc[0, "net_cash_flow"] = 500.0
    assert found(t, "DQ-09", "WARNING")


def test_dq10_negative_fixed_assets():
    t = clean_tables()
    t["balancesheet"].loc[0, "fixed_assets"] = -5.0
    assert found(t, "DQ-10", "WARNING")


def test_dq11_tax_rate_out_of_range():
    t = clean_tables()
    t["profitandloss"].loc[0, "tax_percentage"] = 80.0
    assert found(t, "DQ-11", "WARNING")


def test_dq12_dividend_payout_above_cap():
    t = clean_tables()
    t["profitandloss"].loc[0, "dividend_payout"] = 250.0
    assert found(t, "DQ-12", "WARNING")


def test_dq14_eps_sign_inconsistent():
    t = clean_tables()
    t["profitandloss"].loc[0, "eps"] = -1.0
    assert found(t, "DQ-14", "WARNING")


def test_dq16_short_history():
    t = clean_tables()
    keep = ~(
        (t["profitandloss"]["company_id"] == "BBB")
        & (t["profitandloss"]["year"] > "2021-03")
    )
    t["profitandloss"] = t["profitandloss"][keep]
    res = validate(t)
    hit = res[
        (res["rule_id"] == "DQ-16")
        & (res["company_id"] == "BBB")
        & (res["severity"] == "WARNING")
    ]
    assert not hit.empty
