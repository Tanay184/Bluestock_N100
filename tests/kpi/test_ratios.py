"""Formula tests: profitability, leverage, efficiency."""

import pytest

from src.analytics import ratios as r


def test_npm_normal():
    assert r.net_profit_margin(100, 500) == pytest.approx(20.0)


def test_npm_zero_sales():
    assert r.net_profit_margin(100, 0) is None


def test_opm_mismatch_flagged():
    assert r.opm_mismatch(30.0, 20, 100) is True


def test_opm_within_tolerance():
    assert r.opm_mismatch(20.4, 20, 100) is False


def test_roe_positive():
    assert r.roe(100, 100, 400) == pytest.approx(20.0)


def test_roe_negative_equity_is_none():
    assert r.roe(100, 10, -60) is None


def test_roce_normal():
    assert r.roce(300, 100, 100, 400, 500) == pytest.approx(20.0)


def test_roa_and_zero_assets():
    assert r.roa(100, 2000) == pytest.approx(5.0)
    assert r.roa(100, 0) is None


def test_de_debt_free_returns_zero():
    assert r.debt_to_equity(0, 100, 400) == 0.0


def test_de_normal_and_negative_equity():
    assert r.debt_to_equity(500, 100, 400) == pytest.approx(1.0)
    assert r.debt_to_equity(500, 10, -60) is None


def test_high_leverage_flag_rules():
    assert r.high_leverage_flag(6, "Industrials") is True
    assert r.high_leverage_flag(6, "Financials") is False
    assert r.high_leverage_flag(3, "Industrials") is False


def test_icr_normal():
    assert r.interest_coverage(200, 50, 50) == pytest.approx(5.0)


def test_icr_debt_free_none_and_label():
    assert r.interest_coverage(200, 50, 0) is None
    assert r.icr_label(0) == "Debt Free"
    assert r.icr_label(10) is None


def test_icr_warning():
    assert r.icr_warning(1.2) is True
    assert r.icr_warning(2.0) is False


def test_net_debt_and_asset_turnover():
    assert r.net_debt(100, 30) == 70
    assert r.asset_turnover(1000, 500) == pytest.approx(2.0)
    assert r.asset_turnover(1000, 0) is None


def test_book_value_per_share():
    assert r.book_value_per_share(100, 400, 10) == pytest.approx(50.0)
