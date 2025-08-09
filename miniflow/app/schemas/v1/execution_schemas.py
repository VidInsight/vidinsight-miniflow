from enum import Enum

from .base_schemas import *

# ===============================================================================================  EXECUTION SCHEMAS ==
class ExecutionSummary(BaseModel):
    """Execution özet bilgileri - database models'a uygun"""
    id: str
    workflow_id: str
    status: str
    pending_nodes: int
    executed_nodes: int
    started_at: datetime
    ended_at: Optional[datetime] = None

# ===================================================================================================  EXECUTION SEARCH  ==
# REQUEST SCHEMA
class ExecutionSearchRequest(BaseModel):
    """Execution arama/filtreleme request modeli - database models'a uygun"""
    workflow_id: Optional[str] = None
    status: Optional[str] = None

# RESPONSE SCHEMA
class ExecutionSearchResponse(ListResponse):
    """Execution arama response"""
    data: List[ExecutionSummary]

# =======================================================================================================  EXECUTION LIST  ==
# RESPONSE SCHEMA
class ExecutionListResponse(ListResponse):
    """Execution listesi response"""
    data: List[ExecutionSummary]

# ========================================================================================================  EXECUTION GET  ==
# RESPONSE SCHEMA
class ExecutionDetailResponse(DataResponse):
    """Execution detay response"""
    data: ExecutionSummary

# ====================================================================================================  EXECUTION COUNT  ==
# RESPONSE SCHEMA
class ExecutionCountResponse(CountResponse):
    """Execution sayısı response - status ve workflow bazlı gruplamalar ile"""
    execution_count: int

# ===================================================================================================  EXECUTION EXISTS  ==
# RESPONSE SCHEMA
class ExecutionExistsResponse(ExistsResponse):
    """Execution varlık kontrolü response"""
    is_exists: bool

# =================================================================================================  EXECUTION RESULTS  ==
class ExecutionResultsResponse(DataResponse):
    """Execution results response"""
    results: Dict[str, Any]

# =================================================================================================  EXECUTION STATUS  ==
# RESPONSE SCHEMA
class ExecutionStatusResponse(DataResponse):
    """Execution status response"""
    status: str

# =================================================================================================  EXECUTION CANCEL  ==
# RESPONSE SCHEMA
class ExecutionCancelResponse(BaseResponse):
    """Execution iptal response"""
    execution_id: str
    results: Dict[str, Any]
