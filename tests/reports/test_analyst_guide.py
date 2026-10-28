"""Analyst guide tests: at least 10 pages and no command line too wide for the page."""

from reportlab.platypus import Preformatted

from src.reports.analyst_guide import build_guide, story


def test_guide_has_at_least_ten_pages(tmp_path):
    assert build_guide(tmp_path / "guide.pdf") >= 10


def test_code_lines_fit_the_page():
    blocks = [f for f in story() if isinstance(f, Preformatted)]
    assert blocks
    for block in blocks:
        assert max(len(line) for line in block.lines) <= 100
