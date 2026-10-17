"""Tests for the P/E valuation flag."""

import numpy as np
import pytest

from src.analytics.valuation import flag_pe


@pytest.mark.parametrize(
    "pe,med,exp",
    [
        (31, 20, "Caution"),
        (30, 20, "Fair"),
        (14, 20, "Fair"),
        (13, 20, "Discount"),
        (np.nan, 20, "N/A"),
        (-5, 20, "N/A"),
    ],
)
def test_flag_pe(pe, med, exp):
    assert flag_pe(pe, med) == exp
