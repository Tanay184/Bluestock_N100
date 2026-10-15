import re
from collections import Counter
from pathlib import Path

c = Counter()
for line in (
    Path("output/ratio_edge_cases.log").read_text(encoding="utf-8").splitlines()
):
    if "_ANOMALY" in line:
        cat = re.search(r"category=(\w+)", line)
        c[(line.split(" | ")[0], cat.group(1) if cat else "n/a")] += 1
for k, v in sorted(c.items()):
    print(k, v)
