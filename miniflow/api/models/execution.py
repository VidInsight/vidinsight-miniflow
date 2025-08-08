 """
Execution API Models
===================
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from .base import BaseResponse

# Enum'ları database models'den import edelim
from ...database.models import ExecutionStatus, ExecutionOutputStatus, ArchiveReason


# REQUEST MODELS
# ==============================================================
class ExecutionCreateRequest(BaseModel):
    """Execution oluşturma request modeli"""
    workflow_id: str = Field(..., description="Workflow ID")

    class Config:
        use_enum_values = True


# RESPONSE MODELS
# ==============================================================
class ExecutionData(BaseModel):
    """Execution data modeli"""
    id: str = Field(..., description="Execution ID")
    workflow_id: str = Field(..., description="Workflow ID")
    status: str = Field(..., description="Execution durumu")
    pending_nodes: int = Field(..., ge=0, description="Bekleyen node sayısı")
    executed_nodes: int = Field(..., ge=0, description="Çalıştırılan node sayısı")
    results: Dict[str, Any] = Field(..., description="Execution sonuçları")
    started_at: str = Field(..., description="Başlangıç tarihi (ISO format)")
    ended_at: Optional[str] = Field(None, description="Bitiş tarihi (ISO format)")
    created_at: str = Field(..., description="Oluşturulma tarihi (ISO format)")
    updated_at: str = Field(..., description="Güncellenme tarihi (ISO format)")

    class Config:
        from_attributes = True


class ExecutionResponse(BaseResponse):
    """Tek execution response modeli"""
    data: ExecutionData = Field(..., description="Execution verisi")


class ExecutionListData(BaseModel):
    """Execution listesi data modeli"""
    executions: List[ExecutionData] = Field(..., description="Execution listesi")
    total: int = Field(..., ge=0, description="Toplam execution sayısı")
    offset: int = Field(..., ge=0, description="Offset değeri")
    limit: int = Field(..., ge=1, description="Limit değeri")
    has_more: bool = Field(..., description="Daha fazla kayıt var mı")


class ExecutionListResponse(BaseResponse):
    """Execution listesi response modeli"""
    data: ExecutionListData = Field(..., description="Execution listesi verisi")


# EXECUTION INPUT/OUTPUT MODELS
# ==============================================================
class ExecutionInputData(BaseModel):
    """Execution Input data modeli"""
    id: str = Field(..., description="ExecutionInput ID")
    execution_id: str = Field(..., description="Execution ID")
    node_id: str = Field(..., description="Node ID")
    priority: int = Field(..., description="Öncelik")
    dependency_count: int = Field(..., ge=0, description="Bağımlılık sayısı")
    wait_factor: int = Field(..., ge=0, description="Bekleme faktörü")
    node_name: str = Field(..., description="Node adı")
    script_path: Optional[str] = Field(None, description="Script yolu")
    node_params: Dict[str, Any] = Field(..., description="Node parametreleri")
    created_at: str = Field(..., description="Oluşturulma tarihi (ISO format)")
    updated_at: str = Field(..., description="Güncellenme tarihi (ISO format)")

    class Config:
        from_attributes = True


class ExecutionInputResponse(BaseResponse):
    """ExecutionInput response modeli"""
    data: ExecutionInputData = Field(..., description="ExecutionInput verisi")


class ExecutionOutputData(BaseModel):
    """Execution Output data modeli"""
    id: str = Field(..., description="ExecutionOutput ID")
    execution_id: str = Field(..., description="Execution ID")
    node_id: str = Field(..., description="Node ID")
    status: str = Field(..., description="Output durumu")
    result_data: Optional[Dict[str, Any]] = Field(None, description="Sonuç verisi")
    started_at: Optional[str] = Field(None, description="Başlangıç tarihi (ISO format)")
    ended_at: Optional[str] = Field(None, description="Bitiş tarihi (ISO format)")
    created_at: str = Field(..., description="Oluşturulma tarihi (ISO format)")
    updated_at: str = Field(..., description="Güncellenme tarihi (ISO format)")

    class Config:
        from_attributes = True


class ExecutionOutputResponse(BaseResponse):
    """ExecutionOutput response modeli"""
    data: ExecutionOutputData = Field(..., description="ExecutionOutput verisi")


# ARCHIVED EXECUTION MODELS
# ==============================================================
class ArchivedExecutionData(BaseModel):
    """Archived Execution data modeli"""
    id: str = Field(..., description="ArchivedExecution ID")
    original_execution_id: str = Field(..., description="Orijinal execution ID")
    workflow_id: str = Field(..., description="Workflow ID")
    status: str = Field(..., description="Execution durumu")
    success: bool = Field(..., description="Başarılı mı")
    results: Dict[str, Any] = Field(..., description="Execution sonuçları")
    started_at: str = Field(..., description="Başlangıç tarihi (ISO format)")
    ended_at: Optional[str] = Field(None, description="Bitiş tarihi (ISO format)")
    archived_at: str = Field(..., description="Arşivlenme tarihi (ISO format)")
    archive_reason: str = Field(..., description="Arşivlenme nedeni")
    created_at: str = Field(..., description="Oluşturulma tarihi (ISO format)")
    updated_at: str = Field(..., description="Güncellenme tarihi (ISO format)")

    class Config:
        from_attributes = True


class ArchivedExecutionResponse(BaseResponse):
    """ArchivedExecution response modeli"""
    data: ArchivedExecutionData = Field(..., description="ArchivedExecution verisi")
