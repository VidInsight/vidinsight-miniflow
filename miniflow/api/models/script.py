"""
Script API Models
================
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from .base import BaseResponse

# Enum'ları database models'den import edelim
from ...database.models import ScriptType, ScriptTestStatus


# REQUEST MODELS
# ==============================================================
class ScriptCreateRequest(BaseModel):
    """Script oluşturma request modeli"""
    name: str = Field(..., min_length=1, max_length=100, description="Script adı")
    description: Optional[str] = Field(None, description="Script açıklaması")
    language: ScriptType = Field(ScriptType.PYTHON, description="Script dili")
    type: str = Field("python", description="Script tipi")
    script_path: str = Field(..., description="Script dosya yolu")
    input_params: Dict[str, Any] = Field(default_factory=dict, description="Giriş parametreleri")
    output_params: Dict[str, Any] = Field(default_factory=dict, description="Çıkış parametreleri")
    test_status: ScriptTestStatus = Field(ScriptTestStatus.UNTESTED, description="Test durumu")

    class Config:
        use_enum_values = True


class ScriptUpdateRequest(BaseModel):
    """Script güncelleme request modeli"""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Script adı")
    description: Optional[str] = Field(None, description="Script açıklaması")
    language: Optional[ScriptType] = Field(None, description="Script dili")
    type: Optional[str] = Field(None, description="Script tipi")
    script_path: Optional[str] = Field(None, description="Script dosya yolu")
    input_params: Optional[Dict[str, Any]] = Field(None, description="Giriş parametreleri")
    output_params: Optional[Dict[str, Any]] = Field(None, description="Çıkış parametreleri")
    test_status: Optional[ScriptTestStatus] = Field(None, description="Test durumu")

    class Config:
        use_enum_values = True


# RESPONSE MODELS
# ==============================================================
class ScriptData(BaseModel):
    """Script data modeli"""
    id: str = Field(..., description="Script ID")
    name: str = Field(..., description="Script adı")
    description: Optional[str] = Field(None, description="Script açıklaması")
    language: str = Field(..., description="Script dili")
    type: str = Field(..., description="Script tipi")
    script_path: str = Field(..., description="Script dosya yolu")
    input_params: Dict[str, Any] = Field(..., description="Giriş parametreleri")
    output_params: Dict[str, Any] = Field(..., description="Çıkış parametreleri")
    test_status: str = Field(..., description="Test durumu")
    created_at: str = Field(..., description="Oluşturulma tarihi (ISO format)")
    updated_at: str = Field(..., description="Güncellenme tarihi (ISO format)")

    class Config:
        from_attributes = True


class ScriptResponse(BaseResponse):
    """Tek script response modeli"""
    data: ScriptData = Field(..., description="Script verisi")


class ScriptListData(BaseModel):
    """Script listesi data modeli"""
    scripts: List[ScriptData] = Field(..., description="Script listesi")
    total: int = Field(..., ge=0, description="Toplam script sayısı")
    offset: int = Field(..., ge=0, description="Offset değeri")
    limit: int = Field(..., ge=1, description="Limit değeri")
    has_more: bool = Field(..., description="Daha fazla kayıt var mı")


class ScriptListResponse(BaseResponse):
    """Script listesi response modeli"""
    data: ScriptListData = Field(..., description="Script listesi verisi")
