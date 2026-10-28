"""Peer group endpoints."""

import re
import sqlite3

from fastapi import APIRouter, HTTPException, Query

from src.analytics.peer import LABELS, RADAR, minmax
from src.api.deps import CONN, clean_dict, get_snapshot, require_company, rows

router = APIRouter(tags=["peers"])


def resolve_group(conn: sqlite3.Connection, name: str) -> str | None:
    """Match a peer group name case-insensitively (underscores and hyphens count as spaces)."""
    key = re.sub(r"[\s_\-]+", " ", name).strip().lower()
    for (g,) in conn.execute("SELECT DISTINCT peer_group_name FROM peer_groups"):
        if re.sub(r"[\s_\-]+", " ", g).strip().lower() == key:
            return g
    return None


@router.get("/peers/{group_name}")
def peer_group(group_name: str, conn: sqlite3.Connection = CONN) -> dict:
    """Companies in a peer group with their percentile rank (0-1, 1 = best) on each metric."""
    group = resolve_group(conn, group_name)
    if group is None:
        raise HTTPException(
            status_code=404, detail=f"Peer group '{group_name}' not found"
        )
    members = rows(
        conn,
        "SELECT g.company_id, g.is_benchmark, c.company_name FROM peer_groups g "
        "JOIN companies c ON c.id = g.company_id WHERE g.peer_group_name = ? ORDER BY g.company_id",
        (group,),
    )
    pp = rows(
        conn,
        "SELECT company_id, metric, value, percentile_rank FROM peer_percentiles WHERE peer_group = ?",
        (group,),
    )
    by_company: dict[str, dict] = {
        m["company_id"]: {"percentile_rank": {}, "values": {}} for m in members
    }
    for r in pp:
        if r["company_id"] in by_company:
            by_company[r["company_id"]]["percentile_rank"][r["metric"]] = r[
                "percentile_rank"
            ]
            by_company[r["company_id"]]["values"][r["metric"]] = r["value"]
    companies = [
        {
            "company_id": m["company_id"],
            "company_name": m["company_name"],
            "is_benchmark": bool(m["is_benchmark"]),
            **by_company[m["company_id"]],
        }
        for m in members
    ]
    benchmark = next((c["company_id"] for c in companies if c["is_benchmark"]), None)
    return {"peer_group": group, "benchmark": benchmark, "companies": companies}


@router.get("/companies/{ticker}/peers/compare")
def peer_compare(
    ticker: str,
    group: str | None = Query(
        None, description="Peer group (default: first group of the company)"
    ),
    conn: sqlite3.Connection = CONN,
) -> dict:
    """Radar data: 8 metric values for the company, the peer-group average and the benchmark company."""
    company = require_company(conn, ticker)
    groups = [
        r["peer_group_name"]
        for r in rows(
            conn,
            "SELECT peer_group_name FROM peer_groups WHERE company_id = ? ORDER BY peer_group_name",
            (company["id"],),
        )
    ]
    if not groups:
        raise HTTPException(
            status_code=404, detail=f"{company['id']} is not in any peer group"
        )
    if group:
        chosen = resolve_group(conn, group)
        if chosen is None or chosen not in groups:
            raise HTTPException(
                status_code=404,
                detail=f"{company['id']} is not in peer group '{group}'",
            )
    else:
        chosen = groups[0]
    members = rows(
        conn,
        "SELECT company_id, is_benchmark FROM peer_groups WHERE peer_group_name = ?",
        (chosen,),
    )
    snap = get_snapshot().set_index("company_id")
    ids = [m["company_id"] for m in members if m["company_id"] in snap.index]
    d = snap.loc[ids, RADAR]
    scaled = d.apply(minmax)
    bench = next((m["company_id"] for m in members if m["is_benchmark"]), None)
    return {
        "company_id": company["id"],
        "peer_group": chosen,
        "axes": RADAR,
        "labels": [LABELS[a] for a in RADAR],
        "company": clean_dict(d.loc[company["id"]].to_dict()),
        "peer_group_average": clean_dict(d.mean().to_dict()),
        "benchmark": {
            "company_id": bench,
            "values": clean_dict(d.loc[bench].to_dict()) if bench in d.index else None,
        },
        "scaled_0_100": {
            "company": clean_dict(scaled.loc[company["id"]].to_dict()),
            "peer_group_average": clean_dict(scaled.mean().to_dict()),
        },
    }
