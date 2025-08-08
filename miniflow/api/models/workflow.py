"""
Workflow API Models
==================
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from .base import BaseResponse

# Enum'ları database models'den import edelim
from ...database.models import WorkflowStatus


# REQUEST MODELS
# ==============================================================
class WorkflowCreateRequest(BaseModel):
    """Workflow oluşturma request modeli"""
    name: str = Field(..., min_length=1, max_length=100, description="Workflow adı")
    description: Optional[str] = Field(None, description="Workflow açıklaması")
    status: WorkflowStatus = Field(WorkflowStatus.DRAFT, description="Workflow durumu")
    priority: int = Field(0, ge=0, description="Öncelik seviyesi")

    class Config:
        use_enum_values = True


class WorkflowUpdateRequest(BaseModel):
    """Workflow güncelleme request modeli"""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Workflow adı")
    description: Optional[str] = Field(None, description="Workflow açıklaması")
    status: Optional[WorkflowStatus] = Field(None, description="Workflow durumu")
    priority: Optional[int] = Field(None, ge=0, description="Öncelik seviyesi")

    class Config:
        use_enum_values = True


# RESPONSE MODELS
# ==============================================================
class WorkflowData(BaseModel):
    """Workflow data modeli"""
    id: str = Field(..., description="Workflow ID")
    name: str = Field(..., description="Workflow adı")
    description: Optional[str] = Field(None, description="Workflow açıklaması")
    status: str = Field(..., description="Workflow durumu")
    priority: int = Field(..., description="Öncelik seviyesi")
    created_at: str = Field(..., description="Oluşturulma tarihi (ISO format)")
    updated_at: str = Field(..., description="Güncellenme tarihi (ISO format)")

    class Config:
        from_attributes = True


class WorkflowResponse(BaseResponse):
    """Tek workflow response modeli"""
    data: WorkflowData = Field(..., description="Workflow verisi")


class WorkflowListData(BaseModel):
    """Workflow listesi data modeli"""
    workflows: List[WorkflowData] = Field(..., description="Workflow listesi")
    total: int = Field(..., ge=0, description="Toplam workflow sayısı")
    offset: int = Field(..., ge=0, description="Offset değeri")
    limit: int = Field(..., ge=1, description="Limit değeri")
    has_more: bool = Field(..., description="Daha fazla kayıt var mı")


class WorkflowListResponse(BaseResponse):
    """Workflow listesi response modeli"""
    data: WorkflowListData = Field(..., description="Workflow listesi verisi")
