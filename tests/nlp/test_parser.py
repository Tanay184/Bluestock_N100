"""Tests for the analysis-text parser."""

import pandas as pd
import pytest

from src.nlp.parser import cross_validate, parse_table, parse_text


@pytest.mark.parametrize(
    "text,expected",
    [
        ("10 Years: 21%", (10, 21.0)),
        ("5 Years: 24%", (5, 24.0)),
        ("3 Years 7.5%", (3, 7.5)),
        ("1 Year: 4%", (1, 4.0)),
        ("3 Years: -4.5%", (3, -4.5)),
        ("10years:12%", (10, 12.0)),
        ("TTM: 8%", None),
        ("garbage", None),
        ("", None),
        (None, None),
        (float("nan"), None),
    ],
)
def test_parse_text(text, expected):
    assert parse_text(text) == expected


def test_parse_table_splits_parsed_and_failures():
    df = pd.DataFrame(
        {
            "company_id": ["A", "B"],
            "compounded_sales_growth": ["10 Years: 21%", "oops"],
            "compounded_profit_growth": ["5 Years: 6%", None],
            "stock_price_cagr": [None, None],
            "roe": ["3 Years: 14%", None],
        }
    )
    parsed, failures = parse_table(df)
    assert len(parsed) == 3
    assert failures["company_id"].tolist() == ["B"]
    assert set(parsed.columns) == {
        "company_id",
        "metric_type",
        "period_years",
        "value_pct",
    }


def test_cross_validate_flags_divergence():
    parsed = pd.DataFrame(
        {
            "company_id": ["A", "A", "A"],
            "metric_type": [
                "compounded_sales_growth",
                "compounded_profit_growth",
                "roe",
            ],
            "period_years": [5, 5, 5],
            "value_pct": [20.0, 10.0, 15.0],
        }
    )
    ratios = pd.DataFrame(
        {
            "company_id": ["A"],
            "year": ["2024-03"],
            "revenue_cagr_5yr": [12.0],
            "pat_cagr_5yr": [9.5],
        }
    )
    res = cross_validate(parsed, ratios).set_index("metric_type")["status"]
    assert res["compounded_sales_growth"] == "DIVERGENT"
    assert res["compounded_profit_growth"] == "OK"
    assert res["roe"] == "NOT_COMPARABLE"
