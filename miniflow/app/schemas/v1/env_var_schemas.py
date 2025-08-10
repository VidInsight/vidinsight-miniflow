from .base_schemas import *

# ===================================================================================================  ENV VAR SCHEMAS ==
class EnvVarSummary(BaseModel):
    """Environment Variable özet bilgileri"""
    id: str
    name: str
    value: str
    description: Optional[str] = None

# =====================================================================================================  ENV VAR CREATE  ==
# REQUEST SCHEMA
class EnvVarCreateRequest(BaseModel):
    """Environment Variable oluşturma request modeli"""
    name: str
    value: str
    description: Optional[str] = None

# RESPONSE SCHEMA
class EnvVarCreateResponse(BaseResponse):
    """Environment Variable oluşturma response"""
    env_var_id: str
    name: str
    created_at: datetime

# =====================================================================================================  ENV VAR UPDATE  ==
# REQUEST SCHEMA
class EnvVarUpdateRequest(BaseModel):
    """Environment Variable güncelleme request modeli"""
    name: Optional[str] = None
    value: Optional[str] = None
    description: Optional[str] = None

# RESPONSE SCHEMA
class EnvVarUpdateResponse(BaseResponse):
    """Environment Variable güncelleme response"""
    env_var_id: str
    updated_fields: List[str]
    updated_at: datetime

# =====================================================================================================  ENV VAR DELETE  ==
# RESPONSE SCHEMA
class EnvVarDeleteResponse(BaseResponse):
    """Environment Variable silme response"""
    env_var_id: str
    env_var_name: str

# ===================================================================================================  ENV VAR VALIDATE  ==
# RESPONSE SCHEMA
class EnvVarValidateResponse(BaseResponse):
    """Environment Variable doğrulama response"""
    env_var_id: str
    is_valid: bool
    validation_errors: List[str] = []
    validation_warnings: List[str] = []

# =====================================================================================================  ENV VAR SEARCH  ==
# REQUEST SCHEMA
class EnvVarSearchRequest(BaseModel):
    """Environment Variable arama/filtreleme request modeli"""
    name: Optional[str] = None
    description: Optional[str] = None

# RESPONSE SCHEMA
class EnvVarSearchResponse(ListResponse):
    """Environment Variable arama response"""
    data: List[EnvVarSummary]

# =======================================================================================================  ENV VAR LIST  ==
# RESPONSE SCHEMA
class EnvVarListResponse(ListResponse):
    """Environment Variable listesi response"""
    data: List[EnvVarSummary]

# ========================================================================================================  ENV VAR GET  ==
# RESPONSE SCHEMA
class EnvVarDetailResponse(DataResponse):
    """Environment Variable detay response"""
    data: EnvVarSummary

# ====================================================================================================  ENV VAR COUNT  ==
# RESPONSE SCHEMA
class EnvVarCountResponse(CountResponse):
    """Environment Variable sayısı response"""
    env_var_count: int

# ===================================================================================================  ENV VAR EXISTS  ==
# RESPONSE SCHEMA
class EnvVarExistsResponse(ExistsResponse):
    """Environment Variable varlık kontrolü response"""
    is_exists: bool

# =================================================================================================  ENV VAR DELETE ALL  ==
# RESPONSE SCHEMA
class EnvVarDeleteAllResponse(BaseResponse):
    """Environment Variable toplu silme response"""
    deleted_count: int

