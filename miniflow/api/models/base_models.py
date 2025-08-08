from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional, Dict, Any


# TEMEL RESPONSE MODELI
# ==============================================================
class BaseResponse(BaseModel):
    """Tüm response'lar için base model"""
    status: bool = Field(True, description="true = success, false = error")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


# ERROR RESPONSE
# ==============================================================
class ErrorResponse(BaseResponse):
    """Hata durumunda kullanılacak model"""
    status: bool = Field(False, description="Always False for errors")
    error_code: str = Field(..., description="Hata kodu")
    message: str = Field(..., description="Hata mesajı")
    details: Optional[str] = Field(None, description="Ek detaylar")
