"""
API Version 1 Router

V1 API'sinin tüm endpoint'lerini organize eden router
"""

from fastapi import APIRouter

from .bff import router as web_api_router

# V1 API Router
router = APIRouter()

# Web API'ları dahil et - Ana workflow yönetimi
router.include_router(
    web_api_router,
    prefix="/bff",
    tags=["web-api"]
)

# Status endpoint
@router.get("/status")
async def v1_status():
    """API V1 status kontrolü"""
    return {"message": "API V1 is running", "version": "1.0", "web_api": "active"}
