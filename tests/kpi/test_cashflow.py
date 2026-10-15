"""Cash flow KPI and capital allocation tests."""

import pytest

from src.analytics import cashflow_kpis as ck


def test_fcf_negative_allowed():
    assert ck.free_cash_flow(100, -30) == 70
    assert ck.free_cash_flow(50, -80) == -30


def test_cfo_pat_ratio_and_zero_pat():
    assert ck.cfo_pat_ratio(120, 100) == pytest.approx(1.2)
    assert ck.cfo_pat_ratio(120, 0) is None


@pytest.mark.parametrize(
    "v,label",
    [(1.2, "High Quality"), (0.7, "Moderate"), (0.3, "Accrual Risk"), (None, None)],
)
def test_cfo_quality_label(v, label):
    assert ck.cfo_quality_label(v) == label


@pytest.mark.parametrize(
    "v,label", [(2, "Asset Light"), (5, "Moderate"), (9, "Capital Intensive")]
)
def test_capex_label(v, label):
    assert ck.capex_label(v) == label


def test_capex_intensity_and_fcf_conversion():
    assert ck.capex_intensity(-50, 1000) == pytest.approx(5.0)
    assert ck.fcf_conversion(70, 100) == pytest.approx(70.0)
    assert ck.fcf_conversion(70, 0) is None


@pytest.mark.parametrize(
    "cfo,cfi,cff,pat,exp",
    [
        (100, -50, -30, None, ("+", "-", "-", "Reinvestor")),
        (100, -50, -30, 1.4, ("+", "-", "-", "Shareholder Returns")),
        (-10, 20, 30, None, ("-", "+", "+", "Distress Signal")),
        (100, 20, 30, None, ("+", "+", "+", "Cash Accumulator")),
        (100, -20, 30, None, ("+", "-", "+", "Growth Funded by Debt")),
        (-5, -5, -5, None, ("-", "-", "-", "Pre-Revenue")),
        (None, 1, 1, None, (None, "+", "+", "No Data")),
    ],
)
def test_capital_allocation(cfo, cfi, cff, pat, exp):
    assert ck.capital_allocation(cfo, cfi, cff, pat) == exp
