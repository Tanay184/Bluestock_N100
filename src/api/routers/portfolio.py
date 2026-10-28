"""Portfolio statistics endpoint."""

from fastapi import APIRouter

from src.analytics.clustering import portfolio_stats
from src.api.deps import df_records, get_kpis

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get("/stats")
def stats() -> list[dict]:
    """P10-P90, mean and standard deviation of 10 core KPIs across all companies (latest year)."""
    return df_records(portfolio_stats(get_kpis()))
