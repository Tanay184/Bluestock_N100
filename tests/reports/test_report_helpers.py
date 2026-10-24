"""Tests for report helpers (trend arrows, labels, file names, formatting)."""

import pytest

from src.reports.common import num, year_label
from src.reports.portfolio_report import trend
from src.reports.sector_report import file_name


@pytest.mark.parametrize(
    "latest,prev,lower,exp",
    [
        (12, 10, False, "up"),
        (8, 10, False, "down"),
        (10.1, 10, False, "flat"),
        (9.9, 10, False, "flat"),
        (0.5, 1.0, True, "up"),
        (1.5, 1.0, True, "down"),
        (float("nan"), 10, False, "na"),
        (5, None, False, "na"),
        (0, 0, False, "flat"),
        (3, 0, False, "up"),
    ],
)
def test_trend(latest, prev, lower, exp):
    assert (
        trend(
            latest if latest is not None else float("nan"),
            prev if prev is not None else float("nan"),
            lower,
        )
        == exp
    )


def test_year_label():
    assert year_label("2024-03") == "'24"
    assert year_label("2012-12") == "'12-12"


def test_num_formatting():
    assert num(1234.567, 1) == "1,234.6"
    assert num(None) == "N/A"
    assert num(float("nan")) == "N/A"
    assert num(5, 1, "%") == "5.0%"


def test_sector_file_name():
    assert file_name("Consumer Discretionary") == "Consumer_Discretionary_report.pdf"
    assert file_name("Oil & Gas") == "Oil_Gas_report.pdf"
