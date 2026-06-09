"""API路由模块"""
from .config import router as config_router
from .classify import router as classify_router
from .rules import router as rules_router
from .upload import router as upload_router

__all__ = ["config_router", "classify_router", "rules_router", "upload_router"]