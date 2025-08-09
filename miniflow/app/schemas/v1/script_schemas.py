from .base_schemas import *

# =================================================================================================  SCRIPT SCHEMAS ==
class ScriptSummary(BaseModel):
    """Script özet bilgileri - database models'a uygun"""
    id: str
    name: str
    description: Optional[str] = None
    language: str
    script_path: str
    test_status: str

# =====================================================================================================  SCRIPT CREATE  ==
# REQUEST SCHEMA
class ScriptCreateRequest(BaseModel):
    """Script oluşturma request modeli - database models'a uygun"""
    name: str
    description: Optional[str] = None
    script_content: str
    input_params: Optional[Dict[str, Any]] = {}
    output_params: Optional[Dict[str, Any]] = {}

# RESPONSE SCHEMA
class ScriptCreateResponse(BaseResponse):
    """Script oluşturma response"""
    script_id: str
    name: str
    language: str
    script_path: str

# =====================================================================================================  SCRIPT UPDATE  ==
# REQUEST SCHEMA
class ScriptUpdateRequest(BaseModel):
    """Script güncelleme request modeli - database models'a uygun"""
    name: Optional[str] = None
    description: Optional[str] = None
    script_content: Optional[str] = None
    input_params: Optional[Dict[str, Any]] = None
    output_params: Optional[Dict[str, Any]] = None

# RESPONSE SCHEMA
class ScriptUpdateResponse(BaseResponse):
    """Script güncelleme response"""
    script_id: str
    updated_fields: List[str]

# =====================================================================================================  SCRIPT DELETE  ==
# RESPONSE SCHEMA
class ScriptDeleteResponse(BaseResponse):
    """Script silme response"""
    script_id: str
    script_name: str
    affected_nodes: int = 0

# ===================================================================================================  SCRIPT VALIDATE  ==
# RESPONSE SCHEMA
class ScriptValidateResponse(BaseResponse):
    """Script doğrulama response"""
    script_id: str
    is_valid: bool
    validation_errors: List[str] = []
    validation_warnings: List[str] = []

# =====================================================================================================  SCRIPT SEARCH  ==
# REQUEST SCHEMA
class ScriptSearchRequest(BaseModel):
    """Script arama/filtreleme request modeli - database models'a uygun"""
    name: Optional[str] = None
    description: Optional[str] = None
    language: Optional[str] = None
    test_status: Optional[str] = None

# RESPONSE SCHEMA
class ScriptSearchResponse(ListResponse):
    """Script arama response"""
    data: List[ScriptSummary]

# =====================================================================================================  SCRIPT TEST  ==
# REQUEST SCHEMA
class ScriptTestRequest(BaseModel):
    """Script test çalıştırma request modeli"""
    test_input: Optional[Dict[str, Any]] = {}
    timeout_seconds: Optional[int] = 30
    validate_output: bool = True

# RESPONSE SCHEMA
class ScriptTestResponse(BaseResponse):
    """Script test response"""
    script_id: str
    test_status: str
    execution_time: float
    test_output: Optional[Dict[str, Any]] = None
    test_errors: List[str] = []

# =======================================================================================================  SCRIPT LIST  ==
# RESPONSE SCHEMA
class ScriptListResponse(ListResponse):
    """Script listesi response"""
    data: List[ScriptSummary]

# ========================================================================================================  SCRIPT GET  ==
# RESPONSE SCHEMA
class ScriptDetailResponse(DataResponse):
    """Script detay response"""
    data: ScriptSummary

# ======================================================================================================  SCRIPT COUNT  ==
# RESPONSE SCHEMA
class ScriptCountResponse(CountResponse):
    """Script sayısı response - language ve test status bazlı gruplamalar ile"""
    script_count: int

# =====================================================================================================  SCRIPT EXISTS  ==
# RESPONSE SCHEMA
class ScriptExistsResponse(ExistsResponse):
    """Script varlık kontrolü response"""
    is_exists: bool