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


# SCRIPT MODELLERI
# ==============================================================
# 1. Script Oluşturma - Gelen/Request
class ScriptCreateRequest(BaseModel):
    name: str = Field(..., description="Script name (unique identifier)")
    description: Optional[str] = Field(None, description="Script description")
    file_content: str = Field(..., description="Python script content to upload")
    input_structure: Dict[str, Any] = Field(default_factory=dict, description="Expected input parameters structure")
    output_structure: Dict[str, Any] = Field(default_factory=dict, description="Expected output parameters structure")

# 2. Script Oluşturma - Giden/Response
class ScriptCreateResponse(BaseResponse):
    script_id: str = Field(..., description="Oluşturulan script UUID")
    absolute_path: str = Field(..., description="Script dosya yolu")
    created_at: str = Field(..., description="Oluşturulma zamanı")

# 3. Script Silme - Giden/Response
class ScriptDeleteResponse(BaseResponse):
    script_id: str = Field(..., description="Silinen script UUID")
    script_name: str = Field(..., description="Silinen scriptin adı")
    deleted_at: str = Field(..., description="Silinme zamanı")

# 4. Script Liste Öğesi - Giden/Response
class ScriptListItem(BaseModel):
    script_id: str = Field(..., description="Script UUID")
    name: str = Field(..., description="Script name")
    description: Optional[str] = Field(None, description="Script description")
    language: str = Field(..., description="Script language")
    test_status: str = Field(..., description="Script test status")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")

# 5. Script Listeleme - Giden/Response
class ScriptListResponse(BaseResponse):
    scripts: List[ScriptListItem] = Field(..., description="Script listesi")
    total_count: int = Field(..., description="Toplam script sayısı")
    page: Optional[int] = Field(None, description="Sayfa numarası")
    page_size: Optional[int] = Field(None, description="Sayfa boyutu")

# 6. Script Detay - Giden/Response
class ScriptGetResponse(BaseResponse):
    script_id: str = Field(..., description="Script UUID")
    name: str = Field(..., description="Script name")
    description: Optional[str] = Field(None, description="Script description")
    absolute_path: str = Field(..., description="Absolute path to the stored script file")
    language: str = Field(..., description="Script language")
    input_structure: Dict[str, Any] = Field(default_factory=dict, description="Input parameters structure")
    output_structure: Dict[str, Any] = Field(default_factory=dict, description="Output parameters structure")
    test_status: str = Field(..., description="Script test status")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")
    file_content: Optional[str] = Field(None, description="Script file content (if requested)")


# WORKFLOW MODELLERI
# ==============================================================
# 1. Workflow Oluşturma - Gelen/Request
class WorkflowCreateRequest(BaseModel):
    name: str = Field(..., description="Workflow name (unique identifier)")
    description: Optional[str] = Field(None, description="Workflow description")
    nodes: List[Dict[str, Any]] = Field(..., description="List of workflow nodes")
    edges: List[Dict[str, Any]] = Field(..., description="List of workflow edges")
    triggers: List[Dict[str, Any]] = Field(..., description="List of workflow triggers")

# 2. Workflow Oluşturma - Giden/Response
class WorkflowCreateResponse(BaseResponse):
    workflow_id: str = Field(..., description="Generated workflow UUID")
    created_at: str = Field(..., description="Oluşturulma zamanı")

# 3. Workflow Silme - Giden/Response
class WorkflowDeleteResponse(BaseResponse):
    workflow_id: str = Field(..., description="Deleted workflow UUID")
    workflow_name: str = Field(..., description="Deleted workflow name")
    deleted_at: str = Field(..., description="Silinme zamanı")

# 4. Workflow Güncelleme - Gelen/Request 
class WorkflowUpdateRequest(BaseModel):
    workflow_id: str = Field(..., description="Workflow UUID to update")
    name: Optional[str] = Field(None, description="New workflow name")
    description: Optional[str] = Field(None, description="New workflow description")
    nodes: Optional[List[Dict[str, Any]]] = Field(None, description="New list of workflow nodes")
    edges: Optional[List[Dict[str, Any]]] = Field(None, description="New list of workflow edges")
    triggers: Optional[List[Dict[str, Any]]] = Field(None, description="New list of workflow triggers")

# 5. Workflow Güncelleme - Giden/Response
class WorkflowUpdateResponse(BaseResponse):
    workflow_id: str = Field(..., description="Updated workflow UUID")
    updated_at: str = Field(..., description="Güncellenme zamanı")
    changes_summary: Optional[Dict[str, Any]] = Field(None, description="Yapılan değişikliklerin özeti")

# 6. Workflow Liste Öğesi - Giden/Response
class WorkflowListItem(BaseModel):
    workflow_id: str = Field(..., description="Workflow UUID")
    name: str = Field(..., description="Workflow name")
    description: Optional[str] = Field(None, description="Workflow description")
    status: str = Field(..., description="Workflow status")
    priority: int = Field(..., description="Workflow priority")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")

# 7. Workflow Listeleme - Giden/Response
class WorkflowListResponse(BaseResponse):
    workflows: List[WorkflowListItem] = Field(..., description="Workflow listesi")
    total_count: int = Field(..., description="Toplam workflow sayısı")
    page: Optional[int] = Field(None, description="Sayfa numarası")
    page_size: Optional[int] = Field(None, description="Sayfa boyutu")

# 8. Workflow Detay - Giden/Response
class WorkflowGetResponse(BaseResponse):
    workflow_id: str = Field(..., description="Workflow UUID")
    name: str = Field(..., description="Workflow name")
    description: Optional[str] = Field(None, description="Workflow description")
    status: str = Field(..., description="Workflow status")
    priority: int = Field(..., description="Workflow priority")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")
    nodes: List[Dict[str, Any]] = Field(..., description="List of workflow nodes")
    edges: List[Dict[str, Any]] = Field(..., description="List of workflow edges")
    triggers: List[Dict[str, Any]] = Field(..., description="List of workflow triggers")