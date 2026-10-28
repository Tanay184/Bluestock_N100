"""Export docs/openapi.json and a Postman collection (docs/postman_collection.json) from the FastAPI app."""

import json
import sqlite3
import sys
from contextlib import closing
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.api.main import app
from src.etl.loader import DB_PATH

QUERY_EXAMPLES = {
    "/api/v1/companies": {"sector": "IT"},
    "/api/v1/companies/{ticker}/pl": {"from_year": "2020-03", "to_year": "2024-03"},
    "/api/v1/companies/{ticker}/bs": {"from_year": "2020-03"},
    "/api/v1/companies/{ticker}/cashflow": {"from_year": "2020-03"},
    "/api/v1/companies/{ticker}/ratios": {"year": "2024-03"},
    "/api/v1/screener": {"min_roe": "15", "max_de": "1", "min_fcf": "0"},
    "/api/v1/companies/{ticker}/documents": {"validate": "false"},
}


def path_values() -> dict[str, str]:
    """Example values for path parameters, using a real peer group and sector from the database."""
    with closing(sqlite3.connect(DB_PATH)) as conn:
        group = conn.execute(
            "SELECT DISTINCT peer_group_name FROM peer_groups ORDER BY 1"
        ).fetchone()[0]
    return {"ticker": "TCS", "sector": "Information Technology", "group_name": group}


def main() -> None:
    """Write the OpenAPI document and a Postman v2.1 collection."""
    spec = app.openapi()
    docs = ROOT / "docs"
    docs.mkdir(exist_ok=True)
    (docs / "openapi.json").write_text(json.dumps(spec, indent=2), encoding="utf-8")
    values = path_values()
    items = []
    for path, methods in spec["paths"].items():
        for method, op in methods.items():
            url_path = path
            for name, val in values.items():
                url_path = url_path.replace("{" + name + "}", val)
            query = QUERY_EXAMPLES.get(path, {})
            items.append(
                {
                    "name": f"{method.upper()} {path}",
                    "request": {
                        "method": method.upper(),
                        "description": op.get("summary", ""),
                        "url": {
                            "raw": "{{base_url}}"
                            + url_path
                            + (
                                "?" + "&".join(f"{k}={v}" for k, v in query.items())
                                if query
                                else ""
                            ),
                            "host": ["{{base_url}}"],
                            "path": [p for p in url_path.split("/") if p],
                            "query": [{"key": k, "value": v} for k, v in query.items()],
                        },
                    },
                }
            )
    collection = {
        "info": {
            "name": spec["info"]["title"],
            "version": spec["info"]["version"],
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
        },
        "variable": [{"key": "base_url", "value": "http://localhost:8000"}],
        "item": items,
    }
    (docs / "postman_collection.json").write_text(
        json.dumps(collection, indent=2), encoding="utf-8"
    )
    print(
        f"openapi {spec['openapi']} | endpoints: {len(items)} | wrote docs/openapi.json and docs/postman_collection.json"
    )


if __name__ == "__main__":
    main()
