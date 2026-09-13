"""
Ticket Intelligence — FastAPI Application.
Ticket demand prediction, price analysis, cross-platform comparison,
legal-queue compliance, and alerts for the secondary ticketing market.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import settings
from src.database import close_db, init_db
from src.api.routes import api as api_router
from src.api.routes import api as api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    yield
    # Shutdown
    await close_db()


app = FastAPI(
    title="Ticket Intelligence API",
    description=(
        "API for predicting ticket demand, analyzing resale prices, "
        "comparing platforms, managing a legal compliance queue, "
        "and triggering price/alerts notifications."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.APP_ENV == "development" else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health ────────────────────────────────────────────────────────────────────
@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "ticket-intelligence"}


@app.get("/")
async def root():
    return {
        "service": "Ticket Intelligence",
        "version": "0.1.0",
        "docs": "/docs",
    }


# Routes
app.include_router(api_router)
