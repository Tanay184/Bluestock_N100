"""Tests for screener filters, config and peer percentile maths."""

import numpy as np
import pandas as pd
import pytest

from src.analytics.peer import minmax, pct_rank
from src.analytics.screener import apply_filters, load_config


def test_apply_filters_excludes_nan_and_fails():
    df = pd.DataFrame({"roe": [20, 10, np.nan], "de": [0.5, 0.5, 0.5]})
    out = apply_filters(
        df,
        [
            {"metric": "roe", "op": ">", "value": 15},
            {"metric": "de", "op": "<", "value": 1},
        ],
    )
    assert list(out.index) == [0]


def test_apply_filters_equality_for_debt_free():
    df = pd.DataFrame({"de": [0.0, 0.2]})
    assert len(apply_filters(df, [{"metric": "de", "op": "==", "value": 0}])) == 1


def test_config_has_six_presets():
    assert len(load_config()["presets"]) == 6


def test_pct_rank_higher_is_better():
    assert pct_rank(pd.Series([1.0, 2.0, 3.0, 4.0])).tolist() == pytest.approx(
        [0, 1 / 3, 2 / 3, 1]
    )


def test_pct_rank_lower_is_better():
    assert pct_rank(
        pd.Series([0.1, 0.5, 1.0]), lower_better=True
    ).tolist() == pytest.approx([1, 0.5, 0])


def test_pct_rank_single_member():
    assert pct_rank(pd.Series([5.0])).tolist() == [0.5]


def test_minmax_inverts_de():
    s = pd.Series([0.0, 1.0], name="de")
    assert minmax(s).tolist() == pytest.approx([100, 0])
