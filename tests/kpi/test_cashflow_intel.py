"""Tests for the cash flow intelligence flags."""

import pytest

from src.analytics.cashflow_intel import is_deleveraging, is_distress


@pytest.mark.parametrize(
    "cfo,cff,exp",
    [
        (-10, 5, True),
        (-10, -5, False),
        (10, 5, False),
        (0, 5, False),
        (float("nan"), 5, False),
        (-10, None, False),
    ],
)
def test_is_distress(cfo, cff, exp):
    assert bool(is_distress(cfo, cff)) is exp


@pytest.mark.parametrize(
    "cff,now,prev,exp",
    [
        (-5, 80, 100, True),
        (-5, 120, 100, False),
        (5, 80, 100, False),
        (-5, None, 100, False),
        (-5, 80, float("nan"), False),
    ],
)
def test_is_deleveraging(cff, now, prev, exp):
    assert bool(is_deleveraging(cff, now, prev)) is exp
