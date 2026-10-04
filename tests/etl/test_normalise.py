"""Unit tests for normalize_year and normalize_ticker."""

import pytest

from src.etl.normaliser import PARSE_ERROR as PE
from src.etl.normaliser import normalize_ticker, normalize_year

YEARS = [
    ("Mar-23", "2023-03"),
    ("Mar 23", "2023-03"),
    ("March-2023", "2023-03"),
    ("Mar 2023", "2023-03"),
    ("Dec 2012", "2012-12"),
    ("Dec-22", "2022-12"),
    ("Jun-23", "2023-06"),
    ("FY23", "2023-03"),
    ("FY24", "2024-03"),
    ("FY 2024", "2024-03"),
    ("2023", "2023-03"),
    (2023, "2023-03"),
    (2023.0, "2023-03"),
    ("2023-03", "2023-03"),
    ("2023-12", "2023-12"),
    ("  Mar-24  ", "2024-03"),
    ("MAR-24", "2024-03"),
    ("mar 2014", "2014-03"),
    ("September 2020", "2020-09"),
    ("xyz", PE),
    ("", PE),
    (None, PE),
    ("2023-13", PE),
    ("Foo-23", PE),
]
TICKERS = [
    ("TCS", "TCS"),
    ("tcs", "TCS"),
    (" TCS ", "TCS"),
    ("Tcs", "TCS"),
    ("BAJAJ-AUTO", "BAJAJ-AUTO"),
    ("bajaj-auto", "BAJAJ-AUTO"),
    ("M&M", "M&M"),
    ("m&m", "M&M"),
    ("\tINFY\n", "INFY"),
    ("HDFCBANK", "HDFCBANK"),
    ("  sbin", "SBIN"),
    ("", None),
    ("   ", None),
    (None, None),
    (float("nan"), None),
]


@pytest.mark.parametrize("raw,expected", YEARS)
def test_normalize_year(raw, expected):
    assert normalize_year(raw) == expected


@pytest.mark.parametrize("raw,expected", TICKERS)
def test_normalize_ticker(raw, expected):
    assert normalize_ticker(raw) == expected
