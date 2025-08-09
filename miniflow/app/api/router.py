"""
Ana API Router

Tüm API versiyonlarını organize eden ana router
"""

from fastapi import APIRouter

from .v1 import router as v1_router
from .v2 import router as v2_router

# Ana API Router
api_router = APIRouter()

# API Version 1 - Web API'ları içerir
api_router.include_router(
    v1_router,
    prefix="/v1",
    tags=["api-v1"]
)

# API Version 2 - Gelecekteki geliştirmeler için
api_router.include_router(
    v2_router,
    prefix="/v2",
    tags=["api-v2"]
)