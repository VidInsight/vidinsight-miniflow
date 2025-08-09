"""
API Version 2 Router

V2 API'sinin tüm endpoint'lerini organize eden router
Gelecekteki geliştirmeler için hazırlanmış
"""

from fastapi import APIRouter

# V2 API Router
router = APIRouter()

@router.get("/status")
async def v2_status():
    """API V2 status kontrolü"""
    return {"message": "API V2 is running", "version": "2.0", "status": "development"}

@router.get("/health")
async def health_check():
    """Sağlık kontrolü endpoint'i"""
    return {"status": "healthy", "version": "2.0", "timestamp": "2024-01-01T00:00:00Z"}
