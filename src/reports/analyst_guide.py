"""Analyst guide PDF (Day 44): how to use the screener, dashboard, PDF reports and API."""

from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from src.etl.loader import ROOT
from src.reports.common import (
    CELL,
    CELL_B,
    GREY,
    HEAD,
    LIGHT,
    NAVY,
    SMALL,
    style,
    usable_width,
)

MARGIN = 2.0 * cm
UW = usable_width(A4[0], MARGIN)
H1 = style("g_h1", 17, bold=True, color=NAVY, spaceAfter=8)
H2 = style("g_h2", 11.5, bold=True, color=NAVY, spaceBefore=8, spaceAfter=4)
BODY = style("g_body", 9.5, leading=13.5, spaceAfter=5)
BUL = style(
    "g_bul", 9.5, leading=13.5, leftIndent=14, firstLineIndent=-10, spaceAfter=2
)
CODE = ParagraphStyle(
    "g_code",
    fontName="Courier",
    fontSize=7.6,
    leading=10,
    backColor=LIGHT,
    borderPadding=5,
    spaceBefore=2,
    spaceAfter=7,
)
BASE = "http://localhost:8000/api/v1"
SCREENSHOTS = ROOT / "docs" / "screenshots"


def p(text: str) -> Paragraph:
    """Body paragraph (text is escaped; use ** for nothing, keep plain)."""
    return Paragraph(escape(text), BODY)


def bullets(items: list[str]) -> list:
    """Bulleted list."""
    return [Paragraph("•&nbsp;&nbsp;" + escape(t), BUL) for t in items] + [Spacer(1, 4)]


def code(text: str) -> Preformatted:
    """Monospaced command block."""
    return Preformatted(text.strip("\n"), CODE)


def table(rows: list[list[str]], widths: list[float]) -> Table:
    """Table with a navy header; every cell wraps."""
    data = [[Paragraph(escape(c), HEAD) for c in rows[0]]]
    for r in rows[1:]:
        data.append(
            [Paragraph(escape(c), CELL_B if i == 0 else CELL) for i, c in enumerate(r)]
        )
    t = Table(data, colWidths=[UW * w for w in widths], repeatRows=1)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D0D5DD")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return t


def chapter(num: int, title: str) -> list:
    """Chapter heading."""
    return [Paragraph(f"{num}. {escape(title)}", H1)]


def curl(path: str) -> str:
    """PowerShell-safe curl line for an endpoint path."""
    return f'curl.exe "{BASE}{path}"'


CONTENTS = [
    "Introduction and data caveats",
    "Setup and daily run order",
    "The data pipeline",
    "Starting and navigating the dashboard",
    "Using the Screener",
    "Company Profile, Peers and Trends",
    "Sectors, Capital Allocation and Annual Reports",
    "Generating PDF reports",
    "Using the REST API",
    "Analytics outputs: valuation, cash flow, NLP, clustering",
    "Troubleshooting",
    "KPI reference and glossary",
]


def cover() -> list:
    """Cover page and table of contents."""
    band = Table(
        [
            [
                Paragraph(
                    "<b>Nifty 100 Financial Intelligence Platform</b>",
                    style("c1", 22, color=colors.white, leading=28),
                )
            ],
            [
                Paragraph(
                    "Analyst Guide: screener, dashboard, PDF reports and API",
                    style("c2", 12, color=colors.HexColor("#D6E4F5")),
                )
            ],
        ],
        colWidths=[UW],
    )
    band.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), NAVY),
                ("LEFTPADDING", (0, 0), (-1, -1), 16),
                ("TOPPADDING", (0, 0), (-1, 0), 28),
                ("BOTTOMPADDING", (0, -1), (-1, -1), 28),
            ]
        )
    )
    out = [
        Spacer(1, 3 * cm),
        band,
        Spacer(1, 1 * cm),
        p(
            "Audience: data analysts who run the pipeline, explore the 92-company universe and share results. "
            "No programming is needed to use the dashboard; the command-line steps are copy-and-paste."
        ),
        p(
            "Version 1.0. All monetary values are in Indian Rupees, Crore (Rs Cr) unless stated. "
            "Stock prices and market caps in the source data are simulated and labelled as such."
        ),
        Spacer(1, 0.6 * cm),
        Paragraph("Contents", H2),
    ]
    out += [
        Paragraph(f"{i}.&nbsp;&nbsp;{escape(t)}", BODY)
        for i, t in enumerate(CONTENTS, 1)
    ]
    return out + [PageBreak()]


def story() -> list:
    """All guide pages."""
    s = cover()
    s += chapter(1, "Introduction and data caveats")
    s += [
        p(
            "The platform turns raw financial statements for 92 Nifty 100 companies into 50+ KPIs, a screener, peer "
            "comparison, valuation flags, cash flow intelligence, auto-generated pros and cons, PDF reports, a Streamlit "
            "dashboard and a REST API. Everything is stored in one SQLite file, data/nifty100.db."
        ),
        Paragraph("What is in the database", H2),
        table(
            [
                ["Table", "Contents"],
                [
                    "companies, sectors",
                    "92 companies, 10 broad sectors with companies, sub-sectors",
                ],
                [
                    "profitandloss, balancesheet, cashflow",
                    "Annual statements, FY2010 to FY2024 (financial year ends in March)",
                ],
                [
                    "financial_ratios",
                    "Computed KPIs per company-year: margins, ROE, ROCE, D/E, ICR, CAGR 3/5/10 years, cash flow KPIs, composite score",
                ],
                [
                    "capital_allocation",
                    "Pattern label per company-year from the signs of operating, investing and financing cash flow",
                ],
                [
                    "peer_groups, peer_percentiles",
                    "11 peer groups and the percentile rank of each member on 10 metrics",
                ],
                [
                    "market_cap, stock_prices",
                    "Valuation multiples and monthly prices. SIMULATED data",
                ],
                [
                    "documents, prosandcons, pros_cons_generated",
                    "Annual report links, source pros/cons, rule-generated pros/cons for all companies",
                ],
            ],
            [0.3, 0.7],
        ),
        Spacer(1, 8),
        Paragraph("Things to keep in mind", H2),
    ]
    s += bullets(
        [
            "Market data (prices, market cap, P/E, P/B, EV/EBITDA, dividend yield) is simulated. Use it for screening practice, not for real decisions.",
            "Latest financial year is 2024-03 for almost every company. SIEMENS reports to September.",
            "Banks and NBFCs (sector Financials) are exempt from leverage, coverage and margin rules because high D/E is normal for them.",
            "JIOFIN has only 2 years of history, so it has no tearsheet and several KPIs show N/A.",
            "Pros and cons are generated from KPI threshold rules with a confidence score. They are screening hints, not investment advice.",
        ]
    )
    s += [PageBreak()] + chapter(2, "Setup and daily run order")
    s += [
        p(
            "Open the project folder in VS Code and use the integrated PowerShell terminal. Always run commands from the project root."
        ),
        Paragraph("One-time setup", H2),
        code("""
python -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
"""),
        Paragraph("Every new terminal", H2),
        code(".\\.venv\\Scripts\\Activate.ps1"),
        Paragraph("Rebuild everything from the Excel files (in this order)", H2),
        code("""
python -m src.etl.loader               # Excel -> data/nifty100.db (rebuilds it)
python -m src.analytics.run_ratios     # KPIs, capital allocation labels, edge-case log
python -m src.analytics.screener       # output/screener_output.xlsx
python -m src.analytics.peer           # peer percentiles, peer_comparison.xlsx, radar charts
python -m src.analytics.valuation      # valuation_summary.xlsx, valuation_flags.csv
python -m src.nlp.parser               # analysis_parsed.csv, parse_failures.csv
python -m src.nlp.pros_cons_generator  # pros_cons_generated.csv (and database table)
python -m src.analytics.cashflow_intel # cashflow_intelligence.xlsx, distress_alerts.csv
python -m src.analytics.clustering     # cluster_labels.csv, elbow plot, heatmap, outliers, stats
python -m src.reports.build_reports    # tearsheets, sector reports, portfolio summary
"""),
        p(
            "Warning: the loader deletes and recreates nifty100.db. Run the steps after it again, otherwise the derived "
            "tables (ratios, peers, pros and cons) will be missing. If you only changed one analytics module, run that module alone."
        ),
        Paragraph("Run the applications", H2),
        code("""
streamlit run src/dashboard/app.py        # dashboard at http://localhost:8501
uvicorn src.api.main:app --port 8000      # API at http://localhost:8000/docs
pytest tests/ -q                          # test suite
"""),
        p(
            "The dashboard and the API can run at the same time in two terminals. Stop either one with Ctrl+C."
        ),
    ]
    s += [PageBreak()] + chapter(3, "The data pipeline")
    s += [
        p(
            "The pipeline has four layers. Each layer writes files you can open directly."
        ),
        table(
            [
                ["Layer", "What it does", "Main outputs"],
                [
                    "ETL",
                    "Reads 12 Excel files, normalises tickers and years, runs 16 data-quality rules, loads SQLite",
                    "data/nifty100.db, output/load_audit.csv, output/validation_failures.csv",
                ],
                [
                    "Ratio engine",
                    "Computes KPIs for every company-year with documented edge cases",
                    "financial_ratios table, output/capital_allocation.csv, output/ratio_edge_cases.log",
                ],
                [
                    "Analytics",
                    "Screener, peers, valuation, cash flow intelligence, NLP, clustering",
                    "output/*.xlsx and *.csv, reports/radar_charts, reports/*.png",
                ],
                [
                    "Reports and apps",
                    "PDF reports, dashboard, REST API",
                    "reports/tearsheets, reports/sector, reports/portfolio, src/dashboard, src/api",
                ],
            ],
            [0.18, 0.47, 0.35],
        ),
        Spacer(1, 8),
        Paragraph("Reading the data-quality files", H2),
    ]
    s += bullets(
        [
            "load_audit.csv: rows in, rows out and rejected per table, plus unresolved CRITICAL failures (should be 0).",
            "validation_failures.csv: one row per rule violation with rule_id, table, company_id, year, field, issue and severity (CRITICAL, WARNING or INFO).",
            "Rows removed by design: trailing-twelve-month and partial periods, duplicate company-years, and tickers missing from the company master.",
            "ratio_edge_cases.log: every division by zero, negative equity, debt-free substitution, CAGR turnaround and ROE/ROCE anomaly, with a category.",
        ]
    )
    s += [PageBreak()] + chapter(4, "Starting and navigating the dashboard")
    s += [
        p(
            "Start the dashboard with streamlit run src/dashboard/app.py. The sidebar lists the eight screens. Pages load their data "
            "from the database and cache it for ten minutes, so a freshly rebuilt database appears after the cache expires or after you restart the app."
        ),
        table(
            [
                ["Screen", "Use it to", "Key controls"],
                [
                    "Home",
                    "See market-wide KPIs, the sector mix and the five best companies by quality score",
                    "Year selector in the sidebar (2019 to 2024)",
                ],
                [
                    "Company Profile",
                    "Study one company: KPI tiles, 10-year charts, pros and cons",
                    "Search box (name or ticker), company dropdown",
                ],
                [
                    "Screener",
                    "Filter all 92 companies with 10 sliders or 6 presets and export CSV",
                    "Sidebar sliders, preset buttons, Reset, Download CSV",
                ],
                [
                    "Peer Comparison",
                    "Compare a company with its peer group on a radar chart and a KPI table",
                    "Peer group and company dropdowns",
                ],
                [
                    "Trend Analysis",
                    "Overlay up to 3 metrics over 10 years with year-on-year labels",
                    "Company picker, metric multi-select",
                ],
                [
                    "Sector Analysis",
                    "See revenue versus ROE per sector and sector median KPIs",
                    "Sector dropdown",
                ],
                [
                    "Capital Allocation",
                    "See how companies deploy cash across 8 patterns",
                    "Pattern dropdown below the treemap",
                ],
                [
                    "Annual Reports",
                    "Open annual report PDFs per year",
                    "Company picker, link-check checkbox",
                ],
            ],
            [0.2, 0.5, 0.3],
        ),
        Spacer(1, 8),
        Paragraph("Display conventions", H2),
    ]
    s += bullets(
        [
            "N/A means the value cannot be computed (zero denominator, negative equity, or too little history). It is never zero.",
            "Charts are interactive: hover for values, drag to zoom, double-click to reset, use the camera icon to save a PNG.",
            "Home shows a capped average ROE (5th to 95th percentile) so that a few extreme values do not distort it.",
        ]
    )
    s += [PageBreak()] + chapter(5, "Using the Screener")
    s += [
        p(
            "The screener keeps only companies that satisfy every active filter, then sorts them by the composite screen score "
            "(0 to 100: profitability 35%, cash quality 30%, growth 20%, leverage 15%)."
        ),
        Paragraph("Step by step", H2),
    ]
    s += bullets(
        [
            "Open Screener. All 92 companies are listed because every slider starts switched off (at its extreme).",
            "Click a preset (Quality, Value, Growth, Dividend, Debt-Free, Turnaround) to fill the sliders, or move sliders yourself.",
            "Read the line above the table: N companies match your filters. The table updates as you move a slider.",
            "Presets with conditions that have no slider (for example D/E equal to 0) show them under the count as extra filters.",
            "Press Download CSV to save the table exactly as displayed. Press Reset to clear everything.",
        ]
    )
    s += [
        Paragraph("Preset definitions", H2),
        table(
            [
                ["Preset", "Conditions", "Ranked by"],
                [
                    "Quality",
                    "ROE > 15, D/E < 1, FCF > 0, revenue CAGR 5y > 10",
                    "Screen score",
                ],
                [
                    "Value",
                    "P/E < 20, P/B < 3, D/E < 2, dividend yield > 1",
                    "FCF yield",
                ],
                [
                    "Growth",
                    "PAT CAGR 5y > 20, revenue CAGR 5y > 15, D/E < 2",
                    "PAT CAGR 5y",
                ],
                [
                    "Dividend",
                    "Dividend yield > 2, payout < 80, FCF > 0",
                    "Dividend yield",
                ],
                ["Debt-Free", "D/E = 0, ROE > 12, revenue > 5,000 Cr", "ROE"],
                [
                    "Turnaround",
                    "Revenue CAGR 3y > 10, FCF > 0, D/E falling",
                    "Revenue CAGR 3y",
                ],
            ],
            [0.18, 0.55, 0.27],
        ),
        Spacer(1, 8),
        Paragraph("Tips", H2),
    ]
    s += bullets(
        [
            "Thresholds for the presets live in config/screener_config.yaml. Edit that file to create your own screens, then run python -m src.analytics.screener to refresh the Excel output.",
            "A company with a missing value (N/A) on a filtered metric is excluded, because it cannot be shown to pass.",
            "Sliders for D/E, P/E and P/B are maximums; the others are minimums. Interest coverage treats debt-free companies as passing. The D/E maximum is not applied to Financials (banks and NBFCs).",
            "The same filters are available through the API: GET /api/v1/screener?min_roe=15&max_de=1.",
        ]
    )
    s += [PageBreak()] + chapter(6, "Company Profile, Peers and Trends")
    s += [
        Paragraph("Company Profile", H2),
        p(
            "Type part of a name or ticker in the search box (for example infy), then pick the company. You see six KPI tiles for the latest "
            "year, revenue and net profit bars, a dual-axis ROE and ROCE line chart, and pros and cons. Companies with fewer than 10 years "
            "show a note with the number of years available."
        ),
    ]
    s += [
        Paragraph("Peer Comparison", H2),
        p(
            "Choose one of the 11 peer groups (for example Private Banks or IT Services) and a company. The radar chart scales each of the 8 axes "
            "from 0 to 100 within the group (100 is best; debt-to-equity is inverted). The table below lists every member with the group "
            "benchmark highlighted. Companies that belong to no group (about 36 of 92) have no peer view; their tearsheet radar compares them with their sector."
        ),
    ]
    s += [
        Paragraph("Trend Analysis", H2),
        p(
            "Pick up to three metrics. Each gets its own chart because the units differ. The label on every point is the year-on-year percentage change; it is blank when the "
            "previous value was zero or negative, since a percentage change would be meaningless."
        ),
    ]
    s += [Paragraph("Reading badges in the peer reports", H2)]
    s += bullets(
        [
            "Best in Class: top quartile (75th percentile or higher) on at least 6 of 10 metrics within the group.",
            "Watch List: bottom quartile (25th percentile or lower) on at least 4 of 10 metrics.",
            "Percentile 1.0 is the best member of the group on that metric; 0.0 is the weakest.",
        ]
    )
    s += [PageBreak()] + chapter(7, "Sectors, Capital Allocation and Annual Reports")
    s += [
        Paragraph("Sector Analysis", H2),
        p(
            "Pick a sector to see a bubble chart (revenue on a log scale versus ROE, bubble size is market cap, colour is sub-sector) and a bar chart comparing the "
            "sector's median KPIs with the Nifty 100 median."
        ),
    ]
    s += [
        Paragraph("Capital Allocation", H2),
        p(
            "The label combines the signs of cash flow from operations (CFO), investing (CFI) and financing (CFF) in the latest year."
        ),
        table(
            [
                ["Pattern", "CFO / CFI / CFF", "Reading"],
                [
                    "Reinvestor",
                    "+ / - / -",
                    "Funds growth and repays debt or pays out from operating cash",
                ],
                [
                    "Shareholder Returns",
                    "+ / - / - with CFO well above profit",
                    "Mature cash generator returning cash",
                ],
                [
                    "Liquidating Assets",
                    "+ / + / -",
                    "Selling investments or assets while paying down financing",
                ],
                [
                    "Cash Accumulator",
                    "+ / + / +",
                    "Raising and generating cash on all fronts",
                ],
                [
                    "Growth Funded by Debt",
                    "+ / - / +",
                    "Investing more than it earns, financed by new funding",
                ],
                [
                    "Distress Signal",
                    "- / + / +",
                    "Operations burn cash; funded by financing and asset sales",
                ],
                ["Pre-Revenue", "- / - / -", "Cash leaving through every channel"],
                ["Mixed", "- / - / + or - / + / -", "No clear pattern"],
            ],
            [0.27, 0.3, 0.43],
        ),
        Spacer(1, 6),
        p(
            "Banks often show positive investing cash flow because of how their statements are structured, so read the label for Financials with care."
        ),
    ]
    s += [
        Paragraph("Annual Reports", H2),
        p(
            "Pick a company to list its annual report PDFs from BSE India. Tick the checkbox to test which links still respond; dead links show a red Report unavailable badge. "
            "Some links decay over time, which is expected."
        ),
    ]
    s += [PageBreak()] + chapter(8, "Generating PDF reports")
    s += [
        p("Three kinds of PDF are generated by one command and saved under reports/."),
        table(
            [
                ["Report", "Location", "Contents"],
                [
                    "Company tearsheet (2 pages)",
                    "reports/tearsheets/<TICKER>_tearsheet.pdf",
                    "Page 1: KPI tiles, revenue and profit bars, ROE and ROCE chart. Page 2: balance sheet mix, cash flow waterfall, pros and cons, capital allocation badge",
                ],
                [
                    "Sector report",
                    "reports/sector/<SECTOR>_report.pdf",
                    "Median KPIs versus the whole universe, best and weakest company, table of every company with 8 metrics",
                ],
                [
                    "Portfolio summary",
                    "reports/portfolio/portfolio_summary.pdf",
                    "One page per company in ticker order: 6 KPIs with trend arrows (up = improved, down = declined, right = flat within 2%)",
                ],
            ],
            [0.22, 0.34, 0.44],
        ),
        Spacer(1, 8),
        code("""
python -m src.reports.build_reports --sample   # 5 sample tearsheets only
python -m src.reports.build_reports            # everything (about 40 seconds)
python scripts\\sprint5_check.py                # verifies counts and file sizes
"""),
        Paragraph("Rules and checks", H2),
    ]
    s += bullets(
        [
            "Companies with fewer than 3 years of data are skipped and listed in output/skipped_tearsheets.csv.",
            "Pros and cons must exist first: run python -m src.nlp.pros_cons_generator before building reports.",
            "Every tearsheet should be exactly 2 pages and at least 30 KB. The build prints any that are not.",
            "Open a few PDFs after each full build and check for text overflow or blank pages.",
        ]
    )
    s += [PageBreak()] + chapter(9, "Using the REST API")
    s += [
        p(
            "Start the server with uvicorn src.api.main:app --port 8000. Interactive documentation is at http://localhost:8000/docs "
            "and the machine-readable specification is docs/openapi.json (import docs/postman_collection.json into Postman). "
            "In PowerShell use curl.exe (plain curl is a different command) and keep the quotes around URLs."
        ),
        Paragraph("Examples", H2),
        code(
            "\n".join(
                [
                    curl("/health"),
                    curl("/companies?sector=IT"),
                    curl("/companies/TCS"),
                    curl("/companies/TCS/pl?from_year=2020-03&to_year=2024-03"),
                    curl("/companies/TCS/bs"),
                    curl("/companies/TCS/cashflow"),
                    curl("/companies/TCS/ratios?year=2024-03"),
                ]
            )
        ),
        code(
            "\n".join(
                [
                    curl("/screener?min_roe=15&max_de=1&min_fcf=0"),
                    curl("/sectors"),
                    curl("/sectors/IT/companies"),
                    curl("/peers/IT_Services"),
                    curl("/companies/TCS/peers/compare"),
                    curl("/market-cap/TCS"),
                    curl("/portfolio/stats"),
                    curl("/companies/TCS/documents"),
                ]
            )
        ),
        code(f'curl.exe -o TCS.pdf "{BASE}/companies/TCS/tearsheet"'),
        Paragraph("Endpoint summary (16)", H2),
        table(
            [
                ["Endpoint", "Returns"],
                ["GET /health", "status, row count of every table, uptime, version"],
                [
                    "GET /companies",
                    "All companies; optional sector, market_cap_category, search",
                ],
                [
                    "GET /companies/{ticker}",
                    "Profile plus latest KPIs; 404 for unknown ticker",
                ],
                [
                    "GET /companies/{ticker}/pl | bs | cashflow",
                    "Statement history; optional from_year and to_year (YYYY-MM)",
                ],
                ["GET /companies/{ticker}/ratios", "All KPIs per year; optional year"],
                ["GET /companies/{ticker}/tearsheet", "The tearsheet PDF"],
                [
                    "GET /screener",
                    "Ranked companies; min_roe, max_de, min_fcf, sector, min_rev_cagr_5yr, min_pat_cagr_5yr, max_pe",
                ],
                [
                    "GET /sectors and /sectors/{sector}/companies",
                    "Sector medians; companies of a sector (IT works as an alias)",
                ],
                [
                    "GET /peers/{group} and /companies/{ticker}/peers/compare",
                    "Peer percentiles; radar data versus peer average and benchmark",
                ],
                ["GET /market-cap/{ticker}", "Valuation history (simulated)"],
                [
                    "GET /portfolio/stats",
                    "P10 to P90, mean and standard deviation for 10 KPIs",
                ],
                [
                    "GET /companies/{ticker}/documents",
                    "Annual report links; validate=true checks them live",
                ],
            ],
            [0.42, 0.58],
        ),
        Spacer(1, 8),
        Paragraph("Status codes", H2),
    ]
    s += bullets(
        [
            "200 success. 400 invalid parameter (for example min_roe=abc, or a year not in YYYY-MM format). 404 unknown ticker, sector, peer group or missing tearsheet. 503 database unavailable.",
            "Responses use null for values that cannot be computed. Every response includes an X-Process-Time-ms header.",
        ]
    )
    s += [PageBreak()] + chapter(
        10, "Analytics outputs: valuation, cash flow, NLP, clustering"
    )
    s += [
        table(
            [
                ["File", "What it tells you"],
                [
                    "output/valuation_summary.xlsx, valuation_flags.csv",
                    "P/E, P/B, EV/EBITDA, FCF yield and a flag: Caution if P/E is above 1.5 times the sector median, Discount if below 0.7 times, otherwise Fair",
                ],
                [
                    "output/cashflow_intelligence.xlsx",
                    "CFO quality (5-year CFO/PAT), CapEx intensity, FCF CAGR, FCF conversion, distress and deleveraging flags, capital allocation label",
                ],
                [
                    "output/distress_alerts.csv",
                    "Companies with negative operating cash flow and positive financing cash flow in the latest year",
                ],
                [
                    "output/pattern_changes.csv",
                    "Companies whose capital allocation pattern changed from one year to the next",
                ],
                [
                    "output/pros_cons_generated.csv",
                    "12 pro rules and 12 con rules with a 60 to 100 confidence score; sector-relative fallback entries are marked PRO-REL or CON-REL",
                ],
                [
                    "output/analysis_parsed.csv, cross_validation.csv",
                    "Growth numbers parsed from text and checked against the ratio engine (differences over 5 points are flagged DIVERGENT)",
                ],
                [
                    "output/cluster_labels.csv, cluster_profile.csv",
                    "KMeans (5 clusters) on ROE, D/E, revenue CAGR, FCF CAGR and OPM, with archetype names and the companies closest to each centre",
                ],
                [
                    "reports/elbow_plot.png, correlation_heatmap.png",
                    "Why k = 5, and how the 10 core KPIs move together",
                ],
                [
                    "output/outlier_report.csv",
                    "KPIs more than 3 standard deviations from the sector mean (needs sectors of about 10 or more companies)",
                ],
                [
                    "output/portfolio_stats.csv",
                    "Distribution of each KPI across all 92 companies",
                ],
            ],
            [0.36, 0.64],
        ),
        Spacer(1, 8),
        Paragraph("How to read the cluster names", H2),
        p(
            "Names are assigned automatically from each cluster's average profile and are a starting point. If a name does not fit the companies "
            'listed in cluster_profile.csv, create config/cluster_names.yaml with lines such as  2: "Value Cyclicals"  and run the clustering again.'
        ),
    ]
    s += [PageBreak()] + chapter(11, "Troubleshooting")
    s += [
        table(
            [
                ["Symptom", "Likely cause", "Fix"],
                [
                    "ModuleNotFoundError: No module named 'src'",
                    "Command run from a subfolder or without -m",
                    "cd to the project root and run python -m src.package.module",
                ],
                [
                    "(.venv) not shown, packages missing",
                    "Virtual environment not active",
                    "Run .\\.venv\\Scripts\\Activate.ps1; if blocked: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned",
                ],
                [
                    "Dashboard page shows a red error about a missing table",
                    "Derived tables were wiped by re-running the loader",
                    "Re-run run_ratios, peer, valuation, pros_cons_generator, cashflow_intel",
                ],
                [
                    "Port 8501 or 8000 already in use",
                    "Another dashboard or API is running",
                    "Stop it with Ctrl+C, or start with --server.port 8502 (Streamlit) or --port 8001 (uvicorn)",
                ],
                [
                    "Screener shows 0 companies",
                    "Filters too strict, or an N/A value on a filtered metric",
                    "Press Reset, then add filters one at a time",
                ],
                [
                    "Tearsheet missing for a company",
                    "Fewer than 3 years of data",
                    "Check output/skipped_tearsheets.csv",
                ],
                [
                    "API returns 404 for a peer group",
                    "Name spelled differently",
                    "List groups at /api/v1/peers/{any}; spaces and underscores are interchangeable",
                ],
                [
                    "API screener returns 400",
                    "A parameter is not a number or the sector is unknown",
                    "Check the message in the response body",
                ],
                [
                    "Numbers differ from companies.xlsx",
                    "Source ROE and ROCE use another definition",
                    "The engine value is used for analytics; differences are logged in ratio_edge_cases.log",
                ],
                [
                    "PDF build says problems (not 2 pages or under 30 KB)",
                    "Unusual data for one company",
                    "Open that PDF; re-run the build for it and send the ticker to the maintainer",
                ],
                [
                    "ruff or black reports errors",
                    "Style rules, not functional errors",
                    "Run black src tests scripts and ruff check src tests scripts --fix",
                ],
            ],
            [0.3, 0.3, 0.4],
        )
    ]
    s += [PageBreak()] + chapter(12, "KPI reference and glossary")
    s += [
        table(
            [
                ["KPI", "Formula", "Reading"],
                [
                    "Net profit margin",
                    "net profit / sales x 100",
                    "Above 10% is good, above 20% excellent",
                ],
                [
                    "Operating margin (OPM)",
                    "operating profit / sales x 100",
                    "Cross-checked against the source value",
                ],
                [
                    "ROE",
                    "net profit / (equity capital + reserves) x 100",
                    "None when equity is zero or negative",
                ],
                [
                    "ROCE",
                    "EBIT / (equity + reserves + borrowings) x 100",
                    "EBIT = operating profit minus depreciation",
                ],
                [
                    "Debt-to-equity",
                    "borrowings / (equity + reserves)",
                    "0 means debt-free; above 5 flags non-financials",
                ],
                [
                    "Interest coverage",
                    "(operating profit + other income) / interest",
                    "None when interest is 0 (shown as Debt Free); below 1.5 is a warning",
                ],
                [
                    "Free cash flow",
                    "cash from operations + cash from investing",
                    "Negative is allowed; three negative years is a concern",
                ],
                [
                    "CFO / PAT",
                    "operating cash flow / net profit",
                    "Above 1 high quality, 0.5 to 1 moderate, below 0.5 accrual risk",
                ],
                [
                    "CapEx intensity",
                    "abs(investing cash flow) / sales x 100",
                    "Below 3% asset-light, above 8% capital-intensive",
                ],
                [
                    "CAGR",
                    "((end / start) ^ (1 / years) - 1) x 100",
                    "None with a flag if the start is zero or either value is negative",
                ],
                [
                    "Composite quality score",
                    "0.30 ROE + 0.25 FCF margin + 0.25 ROCE + 0.20 D/E score",
                    "Each part scaled 0 to 100 between the 10th and 90th percentile",
                ],
            ],
            [0.23, 0.42, 0.35],
        ),
        Spacer(1, 8),
        Paragraph("Glossary", H2),
        table(
            [
                ["Term", "Meaning"],
                ["FY", "Financial year, April to March. FY24 is labelled 2024-03."],
                [
                    "CAGR flags",
                    "TURNAROUND (loss to profit), DECLINE_TO_LOSS, BOTH_NEGATIVE, ZERO_BASE, INSUFFICIENT (too little history).",
                ],
                [
                    "Debt-free",
                    "Borrowings equal to zero. D/E is 0 and interest coverage is displayed as Debt Free.",
                ],
                [
                    "Percentile rank",
                    "Position within a peer group from 0 (weakest) to 1 (best).",
                ],
                [
                    "Winsorise",
                    "Clip values to the 5th to 95th (or 10th to 90th) percentile before scaling.",
                ],
                ["Tearsheet", "Two-page company summary PDF."],
            ],
            [0.22, 0.78],
        ),
    ]
    shots = sorted(SCREENSHOTS.glob("*.png")) if SCREENSHOTS.exists() else []
    if shots:
        s += [PageBreak(), Paragraph("Appendix: dashboard screenshots", H1)]
        for i, f in enumerate(shots[:8], 1):
            img = Image(str(f))
            ratio = img.imageHeight / img.imageWidth
            w = UW if ratio < 0.9 else UW * 0.8
            img.drawWidth, img.drawHeight = w, min(w * ratio, 11 * cm)
            s += [
                Paragraph(escape(f.stem.replace("_", " ")), SMALL),
                img,
                Spacer(1, 10),
            ]
            if i % 2 == 0 and i < len(shots[:8]):
                s.append(PageBreak())
    return s


def footer(canvas, doc) -> None:
    """Page footer with page number."""
    canvas.saveState()
    canvas.setFont("DV", 7.5)
    canvas.setFillColor(GREY)
    canvas.drawString(
        MARGIN,
        1.0 * cm,
        "Nifty 100 Financial Intelligence Platform | Analyst Guide v1.0",
    )
    canvas.drawRightString(A4[0] - MARGIN, 1.0 * cm, f"Page {doc.page}")
    canvas.restoreState()


def build_guide(path: Path) -> int:
    """Write the analyst guide PDF; returns the page count."""
    doc = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=2.0 * cm,
        bottomMargin=1.8 * cm,
        title="Nifty 100 Analyst Guide",
        author="Nifty 100 Platform",
    )
    doc.build(story(), onFirstPage=footer, onLaterPages=footer)
    return doc.page


def main() -> None:
    """Build docs/analyst_guide.pdf and report its page count."""
    out = ROOT / "docs" / "analyst_guide.pdf"
    out.parent.mkdir(exist_ok=True)
    pages = build_guide(out)
    print(
        f"{out}: {pages} pages ({'OK' if pages >= 10 else 'BELOW 10'}), {out.stat().st_size // 1024} KB"
    )


if __name__ == "__main__":
    main()
