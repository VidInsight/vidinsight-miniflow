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
    input_params: Dict[str, Any] = Field(default_factory=dict, description="Expected input parameters structure")
    output_params: Dict[str, Any] = Field(default_factory=dict, description="Expected output parameters structure")

# 2. Script Oluşturma - Giden/Response
class ScriptCreateResponse(BaseResponse):
    script_id: str = Field(..., description="Oluşturulan script UUID")
    absolute_path: str = Field(..., description="Script dosya yolu")
    created_at: str = Field(..., description="Oluşturulma zamanı")

# 3. Script Silme - Giden/Response
class ScriptDeleteResponse(BaseResponse):
    script_id: str = Field(..., description="Silinen script UUID")
    script_name: str = Field(..., description="Silinen scriptin adı")

# 6. Script Detay - Giden/Response
class ScriptGetResponse(BaseResponse):
    script_id: str = Field(..., description="Script UUID")
    name: str = Field(..., description="Script name")
    description: Optional[str] = Field(None, description="Script description")
    absolute_path: str = Field(..., description="Absolute path to the stored script file")
    language: str = Field(..., description="Script language")
    input_params: Dict[str, Any] = Field(default_factory=dict, description="Input parameters structure")
    output_params: Dict[str, Any] = Field(default_factory=dict, description="Output parameters structure")
    test_status: str = Field(..., description="Script test status (enum value)")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")
    file_content: Optional[str] = Field(None, description="Script file content (if requested)")

# 5. Script Listeleme - Giden/Response
class ScriptListResponse(BaseResponse):
    scripts: List[ScriptGetResponse] = Field(..., description="Script listesi")
    

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
    nodes: Dict[str, str] = Field(..., description="Created workflow nodes {node_name: node_id}")
    edges: List[str] = Field(..., description="List of created edge IDs")
    triggers: List[str] = Field(..., description="List of created trigger IDs")

# 3. Workflow Silme - Giden/Response
class WorkflowDeleteResponse(BaseResponse):
    workflow_id: str = Field(..., description="Deleted workflow UUID")
    workflow_name: str = Field(..., description="Deleted workflow name")

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

# 7. Workflow Listeleme - Giden/Response
class WorkflowListResponse(BaseResponse):
    workflows: List[WorkflowGetResponse] = Field(..., description="Workflow listesi")

# EXECUTION MODELLERI
# ==============================================================
# 1. Execution Okuma - Giden/Response
class ExecutionCreateResponse(BaseResponse):
    execution_id: str = Field(...)
    pending_nodes: int = Field(...)
    pending_nodes_ids: List[str] = Field(...)
    started_at: str = Field(...)

class ExecutionCancelResponse(BaseResponse):
    execution_id: str = Field(...)
    pending_nodes: int = Field(...)
    executed_nodes: int = Field(...)
    results: dict = Field(...)
    started_at: str = Field(...)

class ExecutionGetResponse(BaseResponse):
    workflow_id: str = Field(...)
    execution_id: str = Field(...)
    status: str = Field(...)
    pending_nodes: int = Field(...)
    executed_nodes: int = Field(...) 
    results: dict = Field(...) 
    started_at: str = Field(...) 
    ended_at: Optional[str] = Field(...) 

class ExecutionListResponse(BaseResponse):
    executions: List[ExecutionGetResponse] = Field(...)


# ENVIRONMENT VARIABLE MODELLERI
# ==============================================================
# 1. Environment Variable Oluşturma - Gelen/Request
class EnvironmentVariableCreateRequest(BaseModel):
    name: str = Field(..., description="Environment variable name (unique identifier)", min_length=1, max_length=255)
    value: str = Field(..., description="Environment variable value", min_length=1)
    description: Optional[str] = Field(None, description="Environment variable description")
    is_active: bool = Field(True, description="Whether the environment variable is active")

# 2. Environment Variable Oluşturma - Giden/Response
class EnvironmentVariableCreateResponse(BaseResponse):
    env_var_id: str = Field(..., description="Created environment variable UUID")
    name: str = Field(..., description="Environment variable name")
    value: str = Field(..., description="Environment variable value")
    is_active: bool = Field(..., description="Whether the environment variable is active")
    created_at: str = Field(..., description="Creation timestamp")

# 3. Environment Variable Güncelleme - Gelen/Request
class EnvironmentVariableUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, description="Environment variable name", min_length=1, max_length=255)
    value: Optional[str] = Field(None, description="Environment variable value", min_length=1)
    description: Optional[str] = Field(None, description="Environment variable description")
    is_active: Optional[bool] = Field(None, description="Whether the environment variable is active")

# 4. Environment Variable Güncelleme - Giden/Response
class EnvironmentVariableUpdateResponse(BaseResponse):
    env_var_id: str = Field(..., description="Updated environment variable UUID")
    name: str = Field(..., description="Environment variable name")
    value: str = Field(..., description="Environment variable value")
    is_active: bool = Field(..., description="Whether the environment variable is active")
    updated_at: str = Field(..., description="Update timestamp")

# 5. Environment Variable Silme - Giden/Response
class EnvironmentVariableDeleteResponse(BaseResponse):
    env_var_id: str = Field(..., description="Deleted environment variable UUID")
    name: str = Field(..., description="Deleted environment variable name")

# 6. Environment Variable Detay - Giden/Response
class EnvironmentVariableGetResponse(BaseResponse):
    env_var_id: str = Field(..., description="Environment variable UUID")
    name: str = Field(..., description="Environment variable name")
    value: str = Field(..., description="Environment variable value")
    description: Optional[str] = Field(None, description="Environment variable description")
    is_active: bool = Field(..., description="Whether the environment variable is active")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")

# 7. Environment Variable Listeleme - Giden/Response
class EnvironmentVariableListResponse(BaseResponse):
    environment_variables: List[EnvironmentVariableGetResponse] = Field(..., description="List of environment variables")