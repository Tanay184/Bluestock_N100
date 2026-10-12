import sqlite3
from pathlib import Path

import pandas as pd

conn = sqlite3.connect("data/nifty100.db")
sql = Path("notebooks/exploratory_queries.sql").read_text()
qs = [q.strip() for q in sql.split(";") if q.strip()]
for i, q in enumerate(qs, 1):
    print(f"\n--- Q{i} ---")
    print(pd.read_sql(q, conn).head(12).to_string(index=False))
