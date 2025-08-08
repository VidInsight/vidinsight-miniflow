"""
Node API Models
==============
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from .base import BaseResponse


# REQUEST MODELS
# ==============================================================
class NodeCreateRequest(BaseModel):
    """Node oluşturma request modeli"""
    workflow_id: str = Field(..., description="Workflow ID")
    script_id: Optional[str] = Field(None, description="Script ID")
    name: str = Field(..., min_length=1, max_length=100, description="Node adı")
    description: Optional[str] = Field(None, description="Node açıklaması")
    params: Dict[str, Any] = Field(default_factory=dict, description="Node parametreleri")
    max_retries: int = Field(3, ge=0, description="Maksimum deneme sayısı")
    timeout_seconds: int = Field(300, ge=1, description="Timeout süresi (saniye)")


class NodeUpdateRequest(BaseModel):
    """Node güncelleme request modeli"""
    script_id: Optional[str] = Field(None, description="Script ID")
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Node adı")
    description: Optional[str] = Field(None, description="Node açıklaması")
    params: Optional[Dict[str, Any]] = Field(None, description="Node parametreleri")
    max_retries: Optional[int] = Field(None, ge=0, description="Maksimum deneme sayısı")
    timeout_seconds: Optional[int] = Field(None, ge=1, description="Timeout süresi (saniye)")


# RESPONSE MODELS
# ==============================================================
class NodeData(BaseModel):
    """Node data modeli"""
    id: str = Field(..., description="Node ID")
    workflow_id: str = Field(..., description="Workflow ID")
    script_id: Optional[str] = Field(None, description="Script ID")
    name: str = Field(..., description="Node adı")
    description: Optional[str] = Field(None, description="Node açıklaması")
    params: Dict[str, Any] = Field(..., description="Node parametreleri")
    max_retries: int = Field(..., description="Maksimum deneme sayısı")
    timeout_seconds: int = Field(..., description="Timeout süresi (saniye)")
    created_at: str = Field(..., description="Oluşturulma tarihi (ISO format)")
    updated_at: str = Field(..., description="Güncellenme tarihi (ISO format)")

    class Config:
        from_attributes = True


class NodeResponse(BaseResponse):
    """Tek node response modeli"""
    data: NodeData = Field(..., description="Node verisi")


class NodeListData(BaseModel):
    """Node listesi data modeli"""
    nodes: List[NodeData] = Field(..., description="Node listesi")
    total: int = Field(..., ge=0, description="Toplam node sayısı")
    offset: int = Field(..., ge=0, description="Offset değeri")
    limit: int = Field(..., ge=1, description="Limit değeri")
    has_more: bool = Field(..., description="Daha fazla kayıt var mı")


class NodeListResponse(BaseResponse):
    """Node listesi response modeli"""
    data: NodeListData = Field(..., description="Node listesi verisi")
