PY = python

load:
	$(PY) -m src.etl.loader

ratios:
	$(PY) -m src.analytics.run_ratios

analytics:
	$(PY) -m src.analytics.screener
	$(PY) -m src.analytics.peer
	$(PY) -m src.analytics.valuation
	$(PY) -m src.nlp.parser
	$(PY) -m src.nlp.pros_cons_generator
	$(PY) -m src.analytics.cashflow_intel
	$(PY) -m src.analytics.clustering

test:
	$(PY) -m pytest tests/ -q --html=reports/pytest_report.html --self-contained-html

report:
	$(PY) -m src.reports.build_reports

dashboard:
	streamlit run src/dashboard/app.py

api:
	uvicorn src.api.main:app --port 8000

clean:
	powershell -NoProfile -Command "Get-ChildItem -Recurse -Include __pycache__,.pytest_cache,.ruff_cache | Remove-Item -Recurse -Force"

.PHONY: load ratios analytics test report dashboard api clean
