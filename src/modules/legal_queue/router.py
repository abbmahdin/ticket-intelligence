"""
FastAPI router for the legal-queue module.
"""
from fastapi import APIRouter, HTTPException, status

from src.modules.legal_queue.schemas import (
    PlatformName,
    PlatformStatus,
    QueueItemCreate,
    QueueItemResponse,
    SyncResult,
)
from src.modules.legal_queue.service import (
    AUTHORIZED_PLATFORMS,
    LegalQueueService,
)

router = APIRouter(prefix="/legal-queue", tags=["legal-queue"])

_service = LegalQueueService()


@router.post("/items", response_model=QueueItemResponse, status_code=status.HTTP_201_CREATED)
async def add_listing(item: QueueItemCreate):
    """Add a verified listing from an authorized reseller to the queue."""
    return await _service.add_listing(item)


@router.get("/items", response_model=list[QueueItemResponse])
async def list_listings(event_id: int | None = None):
    """List queue items, optionally filtered by event."""
    if event_id:
        return await _service.list_event_items(event_id)
    return []


@router.get("/status/{event_id}")
async def get_queue_status(event_id: int):
    """Get queue status for an event."""
    return await _service.get_queue_status(event_id)


@router.post("/sync/{platform}", response_model=SyncResult)
async def sync_platform(platform: str, event_id: int):
    """Sync listings from a platform's API (rate-limited, robots.txt checked)."""
    return await _service.sync_platform(platform, event_id)


@router.get("/platforms", response_model=list[dict])
async def list_platforms():
    """List all authorized resale platforms."""
    return [
        {
            "name": name,
            "base_url": data["base_url"],
            "trust_score": data["trust_score"],
            "rate_limit_per_minute": data["rate_limit_per_minute"],
        }
        for name, data in AUTHORIZED_PLATFORMS.items()
    ]


@router.get("/platforms/{platform_name}/health", response_model=PlatformStatus)
async def check_platform_health(platform_name: str):
    """Check if a platform's API is accessible."""
    if platform_name not in AUTHORIZED_PLATFORMS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Platform '{platform_name}' not found",
        )
    return await _service.check_platform_health(platform_name)