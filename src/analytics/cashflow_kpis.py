"""Cash flow KPIs and the capital allocation classifier."""

from src.analytics.ratios import div, num

# (CFO, CFI, CFF) sign pattern -> label. 0 is treated as '-'.
PATTERNS = {
    ("+", "-", "-"): "Reinvestor",
    ("+", "+", "-"): "Liquidating Assets",
    ("+", "+", "+"): "Cash Accumulator",
    ("-", "+", "+"): "Distress Signal",
    ("+", "-", "+"): "Growth Funded by Debt",
    ("-", "-", "-"): "Pre-Revenue",
    ("-", "-", "+"): "Mixed",
    ("-", "+", "-"): "Mixed",
}


def free_cash_flow(cfo, cfi):
    """FCF = CFO + CFI (negative allowed)."""
    a, b = num(cfo), num(cfi)
    return None if a is None or b is None else a + b


def capex(investing):
    """CapEx proxy = abs(investing activity)."""
    v = num(investing)
    return None if v is None else abs(v)


def cfo_pat_ratio(cfo, pat):
    """CFO / PAT, None if PAT = 0."""
    return div(cfo, pat)


def cfo_quality_label(avg_ratio):
    """5-year average CFO/PAT: >1 High Quality, 0.5-1 Moderate, <0.5 Accrual Risk."""
    v = num(avg_ratio)
    if v is None:
        return None
    if v > 1.0:
        return "High Quality"
    return "Moderate" if v >= 0.5 else "Accrual Risk"


def capex_intensity(investing, sales):
    """abs(investing) / sales x 100."""
    return div(capex(investing), sales, pct=True)


def capex_label(intensity):
    """<3 Asset Light, 3-8 Moderate, >8 Capital Intensive."""
    v = num(intensity)
    if v is None:
        return None
    if v < 3:
        return "Asset Light"
    return "Moderate" if v <= 8 else "Capital Intensive"


def fcf_conversion(fcf, operating_profit):
    """FCF / operating profit x 100, None if operating profit = 0."""
    return div(fcf, operating_profit, pct=True)


def _sign(v):
    v = num(v)
    return None if v is None else ("+" if v > 0 else "-")


def capital_allocation(cfo, cfi, cff, cfo_pat=None):
    """Return (cfo_sign, cfi_sign, cff_sign, pattern_label)."""
    s = (_sign(cfo), _sign(cfi), _sign(cff))
    if None in s:
        return (*s, "No Data")
    label = PATTERNS[s]
    pat = num(cfo_pat)
    if s == ("+", "-", "-") and pat is not None and pat > 1.0:
        label = "Shareholder Returns"
    return (*s, label)
