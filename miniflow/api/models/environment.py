"""
Environment Variable API Models
==============================
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from .base import BaseResponse


# REQUEST MODELS
# ==============================================================
class EnvironmentVariableCreateRequest(BaseModel):
    """Environment Variable oluşturma request modeli"""
    name: str = Field(..., min_length=1, max_length=100, description="Değişken adı")
    value: str = Field(..., max_length=255, description="Değişken değeri")
    description: Optional[str] = Field(None, description="Değişken açıklaması")
    is_sensitive: bool = Field(False, description="Hassas bilgi mi")


class EnvironmentVariableUpdateRequest(BaseModel):
    """Environment Variable güncelleme request modeli"""
    value: Optional[str] = Field(None, max_length=255, description="Değişken değeri")
    description: Optional[str] = Field(None, description="Değişken açıklaması")
    is_sensitive: Optional[bool] = Field(None, description="Hassas bilgi mi")


# RESPONSE MODELS
# ==============================================================
class EnvironmentVariableData(BaseModel):
    """Environment Variable data modeli"""
    id: str = Field(..., description="Environment Variable ID")
    name: str = Field(..., description="Değişken adı")
    value: str = Field(..., description="Değişken değeri")
    description: Optional[str] = Field(None, description="Değişken açıklaması")
    is_sensitive: bool = Field(..., description="Hassas bilgi mi")
    created_at: str = Field(..., description="Oluşturulma tarihi (ISO format)")
    updated_at: str = Field(..., description="Güncellenme tarihi (ISO format)")

    class Config:
        from_attributes = True


class EnvironmentVariableResponse(BaseResponse):
    """Tek environment variable response modeli"""
    data: EnvironmentVariableData = Field(..., description="Environment Variable verisi")


class EnvironmentVariableListData(BaseModel):
    """Environment Variable listesi data modeli"""
    environment_variables: List[EnvironmentVariableData] = Field(..., description="Environment Variable listesi")
    total: int = Field(..., ge=0, description="Toplam environment variable sayısı")
    offset: int = Field(..., ge=0, description="Offset değeri")
    limit: int = Field(..., ge=1, description="Limit değeri")
    has_more: bool = Field(..., description="Daha fazla kayıt var mı")


class EnvironmentVariableListResponse(BaseResponse):
    """Environment Variable listesi response modeli"""
    data: EnvironmentVariableListData = Field(..., description="Environment Variable listesi verisi")
