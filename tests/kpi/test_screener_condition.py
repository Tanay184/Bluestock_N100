"""The D/E upper limit is not applied to Financials (tracker rule)."""

import pandas as pd
import pytest

from src.analytics.screener import apply_filters, condition


@pytest.fixture
def df():
    return pd.DataFrame(
        {
            "broad_sector": ["Financials", "Industrials", "Industrials", "Financials"],
            "de": [8.0, 0.5, 3.0, float("nan")],
            "roe": [15.0, 20.0, 25.0, 12.0],
        }
    )


def test_de_cap_skips_financials(df):
    assert condition(df, "de", "<=", 1.0).tolist() == [True, True, False, True]


def test_strict_de_cap_also_skips_financials(df):
    assert condition(df, "de", "<", 1.0).tolist() == [True, True, False, True]


def test_non_de_metrics_are_unchanged(df):
    assert condition(df, "roe", ">=", 20.0).tolist() == [False, True, True, False]


def test_de_equal_zero_is_not_skipped(df):
    assert condition(df, "de", "==", 0.0).tolist() == [False, False, False, False]


def test_missing_sector_column_is_handled():
    assert condition(pd.DataFrame({"de": [0.5, 3.0]}), "de", "<=", 1.0).tolist() == [
        True,
        False,
    ]


def test_apply_filters_uses_the_skip(df):
    out = apply_filters(
        df,
        [
            {"metric": "de", "op": "<", "value": 1.0},
            {"metric": "roe", "op": ">", "value": 14},
        ],
    )
    assert out["roe"].tolist() == [15.0, 20.0]
