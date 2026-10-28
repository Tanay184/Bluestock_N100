"""FastAPI application for the Nifty 100 Financial Intelligence Platform."""

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from src.api.deps import VERSION, create_indexes
from src.api.routers import (
    companies,
    documents,
    health,
    peers,
    portfolio,
    screener,
    sectors,
    valuation,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("nifty100.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create database indexes on startup."""
    logger.info("startup: %d indexes ensured", create_indexes())
    yield


app = FastAPI(
    title="Nifty 100 Financial Intelligence API",
    description="Read-only JSON API over the Nifty 100 database. Market cap and prices are simulated data.",
    version=VERSION,
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log method, path, status and response time for every request."""
    start = time.perf_counter()
    response = await call_next(request)
    ms = (time.perf_counter() - start) * 1000
    response.headers["X-Process-Time-ms"] = f"{ms:.1f}"
    logger.info(
        "%s %s -> %s in %.1f ms",
        request.method,
        request.url.path,
        response.status_code,
        ms,
    )
    return response


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    """Send the bare address to the interactive documentation."""
    return RedirectResponse(url="/docs")


for module in (
    companies,
    screener,
    sectors,
    peers,
    valuation,
    portfolio,
    documents,
    health,
):
    app.include_router(module.router, prefix="/api/v1")
