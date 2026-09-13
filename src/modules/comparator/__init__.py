"""
Comparator module — legal price comparison across authorized platforms.
"""
from src.modules.comparator.router import router as comparator_router
from src.modules.comparator.service import ComparatorService

__all__ = ["ComparatorService", "comparator_router"]
