"""
Lightweight health-check router reused by the app and the API gateway.
"""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    return {"status": "ok", "module": "health"}
