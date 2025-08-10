from .base_schemas import *

class NodeSummary(BaseModel):
    """Node özet bilgileri - database models'a uygun"""
    id: str
    workflow_id: str
    script_id: Optional[str] = None
    script_name: Optional[str] = None
    name: str
    params: Dict[str, Any] = {}
    outputs: Dict[str, Any] = {}
    max_retries: int = 3
    timeout_seconds: int = 300
    created_at: datetime
    updated_at: datetime

# =====================================================================================================  NODE CREATE  ==
# REQUEST SCHEMA
class NodeCreateRequest(BaseModel):
    """Node oluşturma request modeli - database models'a uygun"""
    workflow_id: str
    script_id: str
    name: str
    params: Dict[str, Any]
    max_retries: Optional[int] = 3
    timeout_seconds: Optional[int] = 300

# RESPONSE SCHEMA
class NodeCreateResponse(BaseResponse):
    """Node oluşturma response"""
    node_id: str
    name: str
    workflow_id: str

# =====================================================================================================  NODE UPDATE  ==
# REQUEST SCHEMA
class NodeUpdateRequest(BaseModel):
    """Node güncelleme request modeli - database models'a uygun"""
    workflow_id: Optional[str] = None
    name: Optional[str] = None
    script_id: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    max_retries: Optional[int] = None
    timeout_seconds: Optional[int] = None

# RESPONSE SCHEMA
class NodeUpdateResponse(BaseResponse):
    """Node güncelleme response"""
    node_id: str
    updated_fields: List[str]

# =====================================================================================================  NODE DELETE  ==
# RESPONSE SCHEMA
class NodeDeleteResponse(BaseResponse):
    """Node silme response"""
    node_id: str
    node_name: str

# ===================================================================================================  NODE VALIDATE  ==
# RESPONSE SCHEMA
class NodeValidateResponse(BaseResponse):
    """Node doğrulama response"""
    node_id: str
    is_valid: bool
    validation_errors: List[str] = []
    validation_warnings: List[str] = []

# =====================================================================================================  NODE SEARCH  ==
# REQUEST SCHEMA
class NodeSearchRequest(BaseModel):
    """Node arama/filtreleme request modeli - database models'a uygun"""
    name: Optional[str] = None
    workflow_id: Optional[str] = None
    script_id: Optional[str] = None

# RESPONSE SCHEMA
class NodeSearchResponse(ListResponse):
    """Node arama response"""
    data: List[NodeSummary]

# =======================================================================================================  NODE LIST  ==
# RESPONSE SCHEMA
class NodeListResponse(ListResponse):
    """Node listesi response"""
    data: List[NodeSummary]

# ========================================================================================================  NODE GET  ==
# RESPONSE SCHEMA
class NodeDetailResponse(DataResponse):
    """Node detay response"""
    data: NodeSummary

# ======================================================================================================  NODE COUNT  ==
# RESPONSE SCHEMA
class NodeCountResponse(CountResponse):
    """Node sayısı response - workflow bazlı gruplamalar ile"""
    node_count: int

# =====================================================================================================  NODE EXISTS  ==
# RESPONSE SCHEMA
class NodeExistsResponse(ExistsResponse):
    """Node varlık kontrolü response"""
    is_exists: bool