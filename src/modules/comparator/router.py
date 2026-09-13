"""
FastAPI router for the comparator module.
"""
from fastapi import APIRouter, HTTPException, status

from src.modules.comparator.schemas import (
    ComparisonRequest,
    ComparisonResult,
    PlatformRating,
)
from src.modules.comparator.service import ComparatorService, AUTHORIZED_PLATFORMS

router = APIRouter(prefix="/comparator", tags=["comparator"])


@router.post("/compare", response_model=ComparisonResult)
async def compare_prices(request: ComparisonRequest):
    """Compare ticket prices across authorized platforms."""
    service = ComparatorService()
    return await service.compare(request)


@router.get("/platforms", response_model=list[PlatformRating])
async def list_authorized_platforms():
    """List all authorized resale platforms."""
    platforms = []
    for name, data in AUTHORIZED_PLATFORMS.items():
        platforms.append(
            PlatformRating(
                platform=name,
                is_authorized=data["is_authorized"],
                trust_score=data["trust_score"],
            )
        )
    return platforms


@router.get("/platforms/{platform_name}", response_model=PlatformRating)
async def get_platform_rating(platform_name: str):
    """Get rating for a specific platform."""
    if platform_name not in AUTHORIZED_PLATFORMS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Platform '{platform_name}' not found",
        )
    data = AUTHORIZED_PLATFORMS[platform_name]
    return PlatformRating(
        platform=platform_name,
        is_authorized=data["is_authorized"],
        trust_score=data["trust_score"],
    )