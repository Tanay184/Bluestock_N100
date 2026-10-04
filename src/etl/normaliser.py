"""Normalisation helpers for NSE tickers and financial-year labels."""

import calendar
import re

import pandas as pd

PARSE_ERROR = "PARSE_ERROR"
_MONTHS = {
    n.lower(): i
    for i in range(1, 13)
    for n in (calendar.month_abbr[i], calendar.month_name[i])
}
_MONTHS["sept"] = 9


def normalize_ticker(value) -> str | None:
    """Strip whitespace and upper-case a ticker; None if empty."""
    if value is None or (not isinstance(value, str) and pd.isna(value)):
        return None
    t = str(value).strip().upper()
    return t or None


def normalize_year(value) -> str:
    """Convert Mar-23 / Mar 2023 / FY23 / 2023 to YYYY-MM, else PARSE_ERROR."""
    if value is None or (not isinstance(value, str) and pd.isna(value)):
        return PARSE_ERROR
    if hasattr(value, "year") and hasattr(value, "month"):
        return f"{value.year}-{value.month:02d}"
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    s = str(value).strip()
    if m := re.fullmatch(r"(\d{4})-(\d{2})", s):
        return s if 1 <= int(m[2]) <= 12 else PARSE_ERROR
    if re.fullmatch(r"\d{4}", s):
        return f"{s}-03"
    if m := re.fullmatch(r"FY[\s\-]*(\d{2}|\d{4})", s.upper()):
        y = int(m[1])
        return f"{y + 2000 if y < 100 else y}-03"
    if m := re.fullmatch(r"([A-Za-z]+)[\s\-/']*(\d{2}|\d{4})", s):
        mon = _MONTHS.get(m[1].lower())
        if mon:
            y = int(m[2])
            return f"{y + 2000 if y < 100 else y}-{mon:02d}"
    return PARSE_ERROR
