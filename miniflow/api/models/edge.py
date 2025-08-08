"""
Edge API Models
==============
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from .base import BaseResponse

# Enum'ları database models'den import edelim
from ...database.models import ConditionType


# REQUEST MODELS
# ==============================================================
class EdgeCreateRequest(BaseModel):
    """Edge oluşturma request modeli"""
    workflow_id: str = Field(..., description="Workflow ID")
    from_node_id: str = Field(..., description="Kaynak node ID")
    to_node_id: str = Field(..., description="Hedef node ID")
    condition_type: ConditionType = Field(ConditionType.SUCCESS, description="Koşul tipi")

    class Config:
        use_enum_values = True


class EdgeUpdateRequest(BaseModel):
    """Edge güncelleme request modeli"""
    condition_type: Optional[ConditionType] = Field(None, description="Koşul tipi")

    class Config:
        use_enum_values = True


# RESPONSE MODELS
# ==============================================================
class EdgeData(BaseModel):
    """Edge data modeli"""
    id: str = Field(..., description="Edge ID")
    workflow_id: str = Field(..., description="Workflow ID")
    from_node_id: str = Field(..., description="Kaynak node ID")
    to_node_id: str = Field(..., description="Hedef node ID")
    condition_type: str = Field(..., description="Koşul tipi")
    created_at: str = Field(..., description="Oluşturulma tarihi (ISO format)")
    updated_at: str = Field(..., description="Güncellenme tarihi (ISO format)")

    class Config:
        from_attributes = True


class EdgeResponse(BaseResponse):
    """Tek edge response modeli"""
    data: EdgeData = Field(..., description="Edge verisi")


class EdgeListData(BaseModel):
    """Edge listesi data modeli"""
    edges: List[EdgeData] = Field(..., description="Edge listesi")
    total: int = Field(..., ge=0, description="Toplam edge sayısı")
    offset: int = Field(..., ge=0, description="Offset değeri")
    limit: int = Field(..., ge=1, description="Limit değeri")
    has_more: bool = Field(..., description="Daha fazla kayıt var mı")


class EdgeListResponse(BaseResponse):
    """Edge listesi response modeli"""
    data: EdgeListData = Field(..., description="Edge listesi verisi")
