from .base_schemas import *
from pydantic import field_validator

# =================================================================================================  WORKFLOW SCHEMAS ==
class WorkflowSummary(BaseModel):
    """Workflow özet bilgileri"""
    id: str
    name: str
    description: Optional[str] = None
    status: str
    priority: int
    node_count: int
    edge_count: int
    created_at: datetime
    updated_at: datetime

class WorkflowDetail(WorkflowSummary):
    """Workflow detay bilgileri"""
    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []
    last_execution_id: Optional[str] = None
    last_execution_status: Optional[str] = None
    last_execution_duration: Optional[float] = None
    execution_count: int = 0

# =================================================================================================  WORKFLOW CREATE  ==
# REQUEST SCHEMA
class WorkflowCreateRequest(BaseModel):
    """Workflow oluşturma request modeli"""
    name: str
    description: Optional[str] = None
    priority: Optional[int] = None
    nodes: Optional[List[Dict[str, Any]]] = None
    edges: Optional[List[Dict[str, Any]]] = None

# RESPONSE SCHEMA
class WorkflowCreateResponse(BaseResponse):
    """Workflow oluşturma response"""
    workflow_id: str
    name: str
    workflow_status: str
    created_at: str
    created_nodes_count: Optional[int] = None
    created_edges_count: Optional[int] = None

# =================================================================================================  WORKFLOW UPDATE  ==
# REQUEST SCHEMA
class WorkflowUpdateRequest(BaseModel):
    """Workflow güncelleme request modeli"""
    name: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[int] = None
    nodes: Optional[List[Dict[str, Any]]] = None
    edges: Optional[List[Dict[str, Any]]] = None

# RESPONSE SCHEMA
class WorkflowUpdateResponse(BaseResponse):
    """Workflow güncelleme response"""
    workflow_id: str
    updated_fields: List[str]
    updated_nodes_count: Optional[int] = None
    updated_edges_count: Optional[int] = None

# =================================================================================================  WORKFLOW DELETE  ==
# RESPONSE SCHEMA
class WorkflowDeleteResponse(BaseResponse):
    """Workflow silme response"""
    workflow_id: str
    workflow_name: str

# ===============================================================================================  WORKFLOW VALIDATE  ==
# RESPONSE SCHEMA
class WorkflowValidateResponse(BaseResponse):
    """Workflow doğrulama response"""
    workflow_id: str
    is_valid: bool
    validation_errors: List[str] = []
    validation_warnings: List[str] = []

# =================================================================================================  WORKFLOW SEARCH  ==
# REQUEST SCHEMA
class WorkflowSearchRequest(BaseModel):
    """Workflow arama/filtreleme request modeli"""
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    tags: Optional[List[str]] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    priority_min: Optional[int] = None
    priority_max: Optional[int] = None
    is_active: Optional[bool] = None

# RESPONSE SCHEMA
class WorkflowSearchResponse(ListResponse):
    """Workflow arama response"""
    data: List[WorkflowSummary]

# ====================================================================================================  WORKFLOW RUN  ==
# RESPONSE SCHEMA
class WorkflowRunResponse(BaseResponse):
    """Workflow çalıştırma response"""
    workflow_id: str
    execution_id: str

# ==================================================================================================  WORKFLOW CLONE  ==
# REQUEST SCHEMA
class WorkflowCloneRequest(BaseModel):
    """Workflow klonlama request modeli"""
    new_name: str
    new_description: Optional[str] = None
    include_nodes: bool = True
    include_edges: bool = True
    copy_executions: bool = False

# RESPONSE SCHEMA
class WorkflowCloneResponse(BaseResponse):
    """Workflow klonlama response"""
    source_workflow_id: str
    new_workflow_id: str
    new_workflow_name: str
    cloned_at: datetime
    cloned_components: Dict[str, int]

# ===================================================================================================  WORKFLOW LIST  ==
# Response Models (BaseResponse extend ederek)
class WorkflowListResponse(ListResponse):
    """Workflow listesi response"""
    data: List[WorkflowSummary]

# ====================================================================================================  WORKFLOW GET  ==
class WorkflowDetailResponse(DataResponse):
    """Workflow detay response"""
    data: WorkflowDetail

# ==================================================================================================  WORKFLOW COUNT  ==
# Count ve Exists responses (base_schemas.py'den inherit)
class WorkflowCountResponse(CountResponse):
    """Workflow sayısı response"""
    workflow_count: int

# =================================================================================================  WORKFLOW EXISTS  ==
class WorkflowExistsResponse(ExistsResponse):
    """Workflow varlık kontrolü response"""
    is_exists: bool