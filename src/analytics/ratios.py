"""Profitability, leverage and efficiency formulas as pure functions."""

import math


def num(x):
    """Return x as float, or None if missing/NaN/non-numeric."""
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(v) else v


def div(a, b, pct=False):
    """Return a / b (x100 if pct); None if an input is missing or b is 0."""
    a, b = num(a), num(b)
    if a is None or b is None or b == 0:
        return None
    return a / b * (100 if pct else 1)


def equity(equity_capital, reserves):
    """Total equity = capital + reserves; None if either is missing."""
    e, r = num(equity_capital), num(reserves)
    return None if e is None or r is None else e + r


def net_profit_margin(net_profit, sales):
    """Net profit margin %, None if sales = 0."""
    return div(net_profit, sales, pct=True)


def operating_profit_margin(operating_profit, sales):
    """Operating profit margin %, None if sales = 0."""
    return div(operating_profit, sales, pct=True)


def opm_mismatch(opm_pct, operating_profit, sales, tol=1.0):
    """True if source OPM differs from computed OPM by more than tol points."""
    calc, src = operating_profit_margin(operating_profit, sales), num(opm_pct)
    return calc is not None and src is not None and abs(src - calc) > tol


def roe(net_profit, equity_capital, reserves):
    """Return on equity %, None if equity + reserves <= 0."""
    eq = equity(equity_capital, reserves)
    return None if eq is None or eq <= 0 else div(net_profit, eq, pct=True)


def ebit(operating_profit, depreciation):
    """EBIT = operating profit - depreciation."""
    o, d = num(operating_profit), num(depreciation)
    return None if o is None or d is None else o - d


def roce(operating_profit, depreciation, equity_capital, reserves, borrowings):
    """ROCE % = EBIT / (equity + reserves + borrowings)."""
    e, eq, b = (
        ebit(operating_profit, depreciation),
        equity(equity_capital, reserves),
        num(borrowings),
    )
    if e is None or eq is None or b is None or eq + b <= 0:
        return None
    return e / (eq + b) * 100


def roa(net_profit, total_assets):
    """Return on assets %, None if total assets = 0."""
    return div(net_profit, total_assets, pct=True)


def debt_to_equity(borrowings, equity_capital, reserves):
    """D/E ratio; 0 (not None) when borrowings = 0; None if equity <= 0."""
    b = num(borrowings)
    if b is None:
        return None
    if b == 0:
        return 0.0
    eq = equity(equity_capital, reserves)
    return None if eq is None or eq <= 0 else b / eq


def high_leverage_flag(de, broad_sector):
    """True if D/E > 5 for a non-Financials company (banks/NBFCs are exempt)."""
    return de is not None and de > 5 and broad_sector != "Financials"


def interest_coverage(operating_profit, other_income, interest):
    """(operating profit + other income) / interest; None if interest = 0."""
    i, o = num(interest), num(operating_profit)
    if i is None or i == 0 or o is None:
        return None
    return (o + (num(other_income) or 0.0)) / i


def icr_label(interest):
    """'Debt Free' when interest = 0, else None."""
    return "Debt Free" if num(interest) == 0 else None


def icr_warning(icr):
    """True if ICR < 1.5 (risk of not covering interest)."""
    return icr is not None and icr < 1.5


def net_debt(borrowings, investments):
    """Net debt = borrowings - investments (liquid asset proxy)."""
    b, i = num(borrowings), num(investments)
    return None if b is None or i is None else b - i


def asset_turnover(sales, total_assets):
    """Sales / total assets, None if assets = 0."""
    return div(sales, total_assets)


def book_value_per_share(equity_capital, reserves, face_value):
    """(equity + reserves) / (equity_capital / face_value), in rupees."""
    eq, ec, fv = equity(equity_capital, reserves), num(equity_capital), num(face_value)
    if eq is None or ec is None or fv is None or ec <= 0 or fv <= 0:
        return None
    return eq / (ec / fv)
