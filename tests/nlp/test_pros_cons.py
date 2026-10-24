"""Tests for the pros/cons rule engine."""

import pandas as pd
import pytest

from src.nlp.pros_cons_generator import Company, all_above, conf, evaluate, streak


def company(sector="Industrials", **cols):
    n = max(len(v) for v in cols.values())
    return Company(
        "X",
        sector,
        pd.DataFrame({k: v for k, v in cols.items()}).reindex(range(n)),
        None,
    )


def test_conf_mapping():
    assert conf(0, 10) is None
    assert conf(-3, 10) is None
    assert conf(None, 10) is None
    assert conf(float("nan"), 10) is None
    assert conf(10, 10) == 100.0
    assert conf(5, 10) == 80.0
    assert conf(50, 10) == 100.0


def test_all_above_and_streak():
    assert all_above([1, 25, 30, 22], 20, 3)
    assert not all_above([25, 30], 20, 3)
    assert streak([1, 2, 3, 4], 3, up=True)
    assert streak([4, 3, 2, 1], 3, up=False)
    assert not streak([1, 3, 2, 4], 3, up=True)
    assert not streak([1, 2], 3, up=True)


def test_high_roe_and_debt_free_pros():
    c = company(return_on_equity_pct=[18, 25, 30, 35], debt_to_equity=[0, 0, 0, 0])
    ids = {e["rule_id"] for e in evaluate(c)}
    assert {"PRO-01", "PRO-03"} <= ids


def test_net_loss_con_and_text():
    c = company(net_profit=[100, 50, -20])
    cons = [e for e in evaluate(c) if e["rule_id"] == "CON-04"]
    assert cons and cons[0]["confidence_pct"] == 95.0
    assert (
        cons[0]["text"]
        == "Company reported a net loss in the most recent financial year"
    )


def test_high_debt_text_contains_value():
    c = company(debt_to_equity=[2.5, 3.0, 4.0])
    e = next(x for x in evaluate(c) if x["rule_id"] == "CON-01")
    assert "4.0x" in e["text"]


def test_financials_exempt_from_leverage_rules():
    c = company(sector="Financials", debt_to_equity=[8.0, 9.0, 10.0])
    assert all(e["rule_id"] != "CON-01" for e in evaluate(c))


@pytest.mark.parametrize("roce", [10, 12])
def test_roce_at_or_above_threshold_is_not_a_con(roce):
    c = company(roce_pct=[roce])
    assert all(e["rule_id"] != "CON-10" for e in evaluate(c))


def test_relative_fallback_skips_de_for_financials_and_uses_best_scope():
    from src.nlp.pros_cons_generator import relative_entries

    row = pd.Series({"debt_to_equity": 8.0, "return_on_equity_pct": 12.0})
    sector_pct = pd.Series({"debt_to_equity": 0.0, "return_on_equity_pct": 0.4})
    universe_pct = pd.Series({"debt_to_equity": 0.0, "return_on_equity_pct": 0.9})
    con = relative_entries("B", row, sector_pct, universe_pct, "con", "Financials")
    assert "Debt-to-equity" not in con["text"]
    pro = relative_entries("B", row, sector_pct, universe_pct, "pro", "Financials")
    assert "Nifty 100 companies" in pro["text"] and pro["confidence_pct"] == 90.0
    assert pro["rule_id"] == "PRO-REL"
