"""Loader tests: every source file is read with the expected row count and column names."""

import pytest

from src.etl.loader import read_all

EXPECTED = {
    "companies": (
        92,
        [
            "id",
            "company_logo",
            "company_name",
            "chart_link",
            "about_company",
            "website",
            "nse_profile",
            "bse_profile",
            "face_value",
            "book_value",
            "roce_percentage",
            "roe_percentage",
        ],
    ),
    "profitandloss": (
        1276,
        [
            "id",
            "company_id",
            "year",
            "sales",
            "expenses",
            "operating_profit",
            "opm_percentage",
            "other_income",
            "interest",
            "depreciation",
            "profit_before_tax",
            "tax_percentage",
            "net_profit",
            "eps",
            "dividend_payout",
        ],
    ),
    "balancesheet": (
        1312,
        [
            "id",
            "company_id",
            "year",
            "equity_capital",
            "reserves",
            "borrowings",
            "other_liabilities",
            "total_liabilities",
            "fixed_assets",
            "cwip",
            "investments",
            "other_asset",
            "total_assets",
        ],
    ),
    "cashflow": (
        1187,
        [
            "id",
            "company_id",
            "year",
            "operating_activity",
            "investing_activity",
            "financing_activity",
            "net_cash_flow",
        ],
    ),
    "analysis": (
        20,
        [
            "id",
            "company_id",
            "compounded_sales_growth",
            "compounded_profit_growth",
            "stock_price_cagr",
            "roe",
        ],
    ),
    "documents": (1585, ["id", "company_id", "Year", "Annual_Report"]),
    "prosandcons": (16, ["id", "company_id", "pros", "cons"]),
    "sectors": (
        92,
        [
            "id",
            "company_id",
            "broad_sector",
            "sub_sector",
            "index_weight_pct",
            "market_cap_category",
        ],
    ),
    "stock_prices": (
        5520,
        [
            "id",
            "company_id",
            "date",
            "open_price",
            "high_price",
            "low_price",
            "close_price",
            "volume",
            "adjusted_close",
        ],
    ),
    "market_cap": (
        552,
        [
            "id",
            "company_id",
            "year",
            "market_cap_crore",
            "enterprise_value_crore",
            "pe_ratio",
            "pb_ratio",
            "ev_ebitda",
            "dividend_yield_pct",
        ],
    ),
    "financial_ratios": (
        1184,
        [
            "id",
            "company_id",
            "year",
            "net_profit_margin_pct",
            "operating_profit_margin_pct",
            "return_on_equity_pct",
            "debt_to_equity",
            "interest_coverage",
            "asset_turnover",
            "free_cash_flow_cr",
            "capex_cr",
            "earnings_per_share",
            "book_value_per_share",
            "dividend_payout_ratio_pct",
            "total_debt_cr",
            "cash_from_operations_cr",
        ],
    ),
    "peer_groups": (56, ["id", "peer_group_name", "company_id", "is_benchmark"]),
}


@pytest.fixture(scope="module")
def tables():
    """Read all twelve Excel files once."""
    return read_all()


def test_all_twelve_files_are_read(tables):
    assert set(tables) == set(EXPECTED)


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_row_count(tables, name):
    assert len(tables[name]) == EXPECTED[name][0]


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_column_names(tables, name):
    assert list(tables[name].columns) == EXPECTED[name][1]
