from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.database import init_db

logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))
logger = logging.getLogger("sentryflow")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("SentryFlow starting up")
    await init_db()
    logger.info("Database initialized")
    yield
    logger.info("SentryFlow shutting down")


def create_app() -> FastAPI:
    app = FastAPI(
        title="SentryFlow",
        description="Agentic Transaction Security Platform",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/v1/health")
    async def health():
        return {"status": "healthy", "service": "sentryflow-gateway"}

    # Route registrations will be added as modules are implemented
    from backend.api import auth, agents, suppliers, gateway, approvals, audit, dashboard, incidents, documents

    app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
    app.include_router(agents.router, prefix="/api/v1/agents", tags=["agents"])
    app.include_router(suppliers.router, prefix="/api/v1/suppliers", tags=["suppliers"])
    app.include_router(gateway.router, prefix="/api/v1/gateway", tags=["gateway"])
    app.include_router(approvals.router, prefix="/api/v1/approvals", tags=["approvals"])
    app.include_router(audit.router, prefix="/api/v1/audit", tags=["audit"])
    app.include_router(incidents.router, prefix="/api/v1/incidents", tags=["incidents"])
    app.include_router(documents.router, prefix="/api/v1/documents", tags=["documents"])
    app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["dashboard"])

    return app


app = create_app()
