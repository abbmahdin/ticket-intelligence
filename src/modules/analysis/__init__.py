"""
Analysis module — historical price data analysis and trend detection.
"""
from src.modules.analysis.router import router as analysis_router
from src.modules.analysis.service import AnalysisService

__all__ = ["AnalysisService", "analysis_router"]
