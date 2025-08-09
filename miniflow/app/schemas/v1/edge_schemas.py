from enum import Enum

from .base_schemas import *

class ConditionTypeSchema(str, Enum):
    """Edge condition türü enum'u - database models'dan"""
    SUCCESS = "success"
    FAILURE = "failure"
    ALWAYS = "always"
    CONDITIONAL = "conditional"

class EdgeSummary(BaseModel):
    """Edge özet bilgileri - database models'a uygun"""
    id: str
    workflow_id: str
    from_node_id: str
    to_node_id: str
    condition_type: ConditionTypeSchema

# =====================================================================================================  EDGE CREATE  ==
# REQUEST SCHEMAS
class EdgeCreateRequest(BaseModel):
    """Edge oluşturma request modeli - database models'a uygun"""
    workflow_id: str
    from_node_id: str
    to_node_id: str
    condition_type: ConditionTypeSchema = ConditionTypeSchema.SUCCESS

# RESPONSE SCHEMAS
class EdgeCreateResponse(BaseResponse):
    """Edge oluşturma response"""
    edge_id: str
    workflow_id: str

# =====================================================================================================  EDGE UPDATE  ==
# REQUEST SCHEMAS
class EdgeUpdateRequest(BaseModel):
    """Edge güncelleme request modeli - database models'a uygun"""
    workflow_id: Optional[str] = None
    from_node_id: Optional[str] = None
    to_node_id: Optional[str] = None
    condition_type: Optional[ConditionTypeSchema] = None

# RESPONSE SCHEMAS
class EdgeUpdateResponse(BaseResponse):
    """Edge güncelleme response"""
    edge_id: str
    updated_fields: List[str]

# =====================================================================================================  EDGE DELETE  ==
# RESPONSE SCHEMAS
class EdgeDeleteResponse(BaseResponse):
    """Edge silme response"""
    edge_id: str
    from_node_name: Optional[str] = None
    to_node_name: Optional[str] = None

# ===================================================================================================  EDGE VALIDATE  ==
# RESPONSE SCHEMAS
class EdgeValidateResponse(BaseResponse):
    """Edge doğrulama response"""
    edge_id: str
    is_valid: bool
    validation_errors: List[str] = []
    validation_warnings: List[str] = []

# =====================================================================================================  EDGE SEARCH  ==
# REQUEST SCHEMAS
class EdgeSearchRequest(BaseModel):
    """Edge arama/filtreleme request modeli - database models'a uygun"""
    workflow_id: Optional[str] = None
    from_node_id: Optional[str] = None
    to_node_id: Optional[str] = None
    condition_type: Optional[ConditionTypeSchema] = None

# RESPONSE SCHEMAS
class EdgeSearchResponse(ListResponse):
    """Edge arama response"""
    data: List[EdgeSummary]

# =======================================================================================================  EDGE LIST  ==
# RESPONSE SCHEMAS
class EdgeListResponse(ListResponse):
    """Edge listesi response"""
    data: List[EdgeSummary]

# ========================================================================================================  EDGE GET  ==
# RESPONSE SCHEMAS
class EdgeDetailResponse(DataResponse):
    """Edge detay response"""
    data: EdgeSummary

# ======================================================================================================  EDGE COUNT  ==
# RESPONSE SCHEMAS
class EdgeCountResponse(CountResponse):
    """Edge sayısı response - workflow ve condition bazlı gruplamalar ile"""
    node_count: int

# =====================================================================================================  EDGE EXISTS  ==
# RESPONSE SCHEMAS
class EdgeExistsResponse(ExistsResponse):
    """Edge varlık kontrolü response"""
    is_exists: bool
