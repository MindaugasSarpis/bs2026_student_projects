"""FastAPI application entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from repops.api.routers import keywords, results, reports, targets
from repops.observability.logging import configure_logging, get_logger
from repops.observability.metrics import start_metrics_server
from repops.settings import settings

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    configure_logging()
    start_metrics_server()
    logger.info("repops_api_starting", environment=settings.environment)
    yield
    logger.info("repops_api_shutting_down")


app = FastAPI(
    title="RepOps",
    description="Reputation Operations — social media monitoring & disinformation reporting",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if not settings.is_production else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(targets.router, prefix="/api/v1/targets", tags=["Targets"])
app.include_router(keywords.router, prefix="/api/v1/keywords", tags=["Keywords"])
app.include_router(results.router, prefix="/api/v1/results", tags=["Analysis Results"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["Reports"])


@app.get("/health", tags=["System"])
def health() -> dict:  # type: ignore[type-arg]
    return {"status": "ok", "version": "0.1.0"}


def run() -> None:
    """Entrypoint for `repops-api` CLI script."""
    import uvicorn
    uvicorn.run("repops.api.main:app", host="0.0.0.0", port=8000, reload=not settings.is_production)
