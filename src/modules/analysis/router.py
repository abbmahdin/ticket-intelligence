"""
FastAPI router for the analysis module.
"""
from fastapi import APIRouter, HTTPException, Query

from src.modules.analysis.schemas import (
    HistoricalPriceQuery,
    MarketSummary,
    PriceStatistics,
    PriceTrend,
)
from src.modules.analysis.service import AnalysisService

router = APIRouter(prefix="/analysis", tags=["analysis"])

# In-memory price store for demo
_price_data: dict[int, list[dict]] = {}


@router.get("/statistics/{event_id}", response_model=PriceStatistics)
async def get_price_statistics(event_id: int, platform: str | None = None):
    """Get price statistics for an event over the last 90 days."""
    service = AnalysisService()
    prices = _price_data.get(event_id, [])
    if platform:
        prices = [p for p in prices if p.get("platform") == platform]
    return await service.compute_statistics([p["price"] for p in prices])


@router.get("/trend/{event_id}", response_model=PriceTrend)
async def get_price_trend(
    event_id: int,
    days: int = Query(default=30, ge=1, le=365),
):
    """Get price trend analysis for an event."""
    service = AnalysisService()
    prices = _price_data.get(event_id, [])
    return await service.detect_trend(prices)


@router.get("/market-summary/{event_id}", response_model=MarketSummary)
async def get_market_summary(event_id: int):
    """Get a comprehensive market summary for an event."""
    service = AnalysisService()
    return await service.get_market_summary(event_id)


@router.get("/events")
async def list_monitored_events():
    """List all events currently monitored."""
    return {"events": list(_price_data.keys())}