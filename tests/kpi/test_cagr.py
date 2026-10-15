"""CAGR engine tests."""

import pandas as pd
import pytest

from src.analytics.cagr import add_cagr, cagr

CASES = [
    (100, 161, 5, 10.0, None),
    (100, 200, 3, 26.0, None),
    (-100, 200, 5, None, "TURNAROUND"),
    (100, -50, 5, None, "DECLINE_TO_LOSS"),
    (-100, -50, 5, None, "BOTH_NEGATIVE"),
    (0, 100, 5, None, "ZERO_BASE"),
    (None, 100, 5, None, "INSUFFICIENT"),
    (100, None, 5, None, "INSUFFICIENT"),
]


@pytest.mark.parametrize("start,end,n,exp,flag", CASES)
def test_cagr_cases(start, end, n, exp, flag):
    val, f = cagr(start, end, n)
    assert f == flag
    if exp is None:
        assert val is None
    else:
        assert val == pytest.approx(exp, abs=0.1)


def test_add_cagr_windows_and_insufficient():
    df = pd.DataFrame(
        {
            "company_id": "X",
            "year": [f"{2019 + i}-03" for i in range(6)],
            "sales": [100 * 1.1**i for i in range(6)],
        }
    )
    out = add_cagr(df, "sales", "revenue")
    last = out[out["year"] == "2024-03"].iloc[0]
    assert last["revenue_cagr_5yr"] == pytest.approx(10.0, abs=0.01)
    assert (
        out[out["year"] == "2023-03"].iloc[0]["revenue_cagr_5yr_flag"] == "INSUFFICIENT"
    )
