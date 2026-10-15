"""CAGR engine with the six edge-case flags."""

from src.analytics.ratios import num


def cagr(start, end, n_years):
    """Return (cagr_pct, flag); flag is None when CAGR is computed normally."""
    s, e = num(start), num(end)
    if s is None or e is None:
        return None, "INSUFFICIENT"
    if s == 0:
        return None, "ZERO_BASE"
    if s > 0 and e > 0:
        return ((e / s) ** (1 / n_years) - 1) * 100, None
    if s > 0:
        return None, "DECLINE_TO_LOSS"
    if e > 0:
        return None, "TURNAROUND"
    return None, "BOTH_NEGATIVE"


def add_cagr(df, value_col, prefix, windows=(3, 5, 10)):
    """Add {prefix}_cagr_{n}yr and {prefix}_cagr_{n}yr_flag columns (year = YYYY-MM)."""
    lookup = df.set_index(["company_id", "year"])[value_col].to_dict()
    for n in windows:
        res = [
            cagr(lookup.get((c, f"{int(y[:4]) - n}-{y[5:]}")), v, n)
            for c, y, v in zip(df["company_id"], df["year"], df[value_col])
        ]
        df[f"{prefix}_cagr_{n}yr"] = [r[0] for r in res]
        df[f"{prefix}_cagr_{n}yr_flag"] = [r[1] for r in res]
    return df
