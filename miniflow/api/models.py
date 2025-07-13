from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

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
class ScriptCreateResponse(BaseModel):
    script_id: str = Field(..., description="Generated script UUID")
    name: str = Field(..., description="Script name")
    description: Optional[str] = Field(None, description="Script description")
    absolute_path: str = Field(..., description="Absolute path to the stored script file")
    language: str = Field(default="python", description="Script language")
    input_structure: Dict[str, Any] = Field(default_factory=dict, description="Input parameters structure")
    output_structure: Dict[str, Any] = Field(default_factory=dict, description="Output parameters structure")
    test_status: str = Field(default="untested", description="Script test status")
    created_at: str = Field(..., description="Creation timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "script_id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "data_processor",
                "description": "Process incoming data",
                "absolute_path": "/path/to/scripts/550e8400-e29b-41d4-a716-446655440000.py",
                "language": "python",
                "input_structure": {"data": "list", "config": "dict"},
                "output_structure": {"result": "dict", "status": "str"},
                "test_status": "untested",
                "created_at": "2024-01-01T12:00:00"
            }
        }

# 3. Script Silme - Gelen/Request 
class ScriptDeleteRequest(BaseModel):
    script_id: str = Field(..., description="Script UUID to delete")
    
    class Config:
        json_schema_extra = {
            "example": {
                "script_id": "550e8400-e29b-41d4-a716-446655440000"
            }
        }

# 4. Script Silme - Giden/Response
class ScriptDeleteReponse(BaseModel):
    success: bool = Field(..., description="Operation success status")
    script_id: str = Field(..., description="Deleted script UUID")
    script_name: str = Field(..., description="Deleted script name")
    message: str = Field(..., description="Operation result message")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "script_id": "550e8400-e29b-41d4-a716-446655440000",
                "script_name": "data_processor",
                "message": "Script deleted successfully"
            }
        }

# 5. Script Listeleme - Giden/Response
class ScriptListResponse(BaseModel):
    script_id: str = Field(..., description="Script UUID")
    name: str = Field(..., description="Script name")
    description: Optional[str] = Field(None, description="Script description")
    language: str = Field(..., description="Script language")
    test_status: str = Field(..., description="Script test status")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "script_id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "data_processor",
                "description": "Process incoming data",
                "language": "python",
                "test_status": "untested",
                "created_at": "2024-01-01T12:00:00",
                "updated_at": "2024-01-01T12:00:00"
            }
        }

# 6. Script Detay - Gelen/Request
class ScriptGetRequest(BaseModel):
    script_id: str = Field(..., description="Script UUID to retrieve")
    
    class Config:
        json_schema_extra = {
            "example": {
                "script_id": "550e8400-e29b-41d4-a716-446655440000"
            }
        }

# 7. Script Detay - Giden/Response
class ScriptGetResponse(BaseModel):
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
    
    class Config:
        json_schema_extra = {
            "example": {
                "script_id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "data_processor",
                "description": "Process incoming data",
                "absolute_path": "/path/to/scripts/data_processor.py",
                "language": "python",
                "input_structure": {"data": "list", "config": "dict"},
                "output_structure": {"result": "dict", "status": "str"},
                "test_status": "untested",
                "created_at": "2024-01-01T12:00:00",
                "updated_at": "2024-01-01T12:00:00",
                "file_content": "#!/usr/bin/env python3\nprint('Hello World')"
            }
        }


# WORKFLOW MODELLERI
# ==============================================================
# 1. Workflow Oluşturma - Gelen/Request
class WorkflowCreateRequest(BaseModel):
    name: str = Field(..., description="Workflow name (unique identifier)")
    description: Optional[str] = Field(None, description="Workflow description")
    nodes: List[Dict[str, Any]] = Field(..., description="List of workflow nodes")
    edges: List[Dict[str, Any]] = Field(..., description="List of workflow edges")
    triggers: List[Dict[str, Any]] = Field(..., description="List of workflow triggers")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "data_processing_workflow",
                "description": "Process data through multiple stages",
                "nodes": [
                    {
                        "name": "data_loader",
                        "script_name": "data_loader_script",
                        "params": {"source": "file"},
                        "max_retries": 3,
                        "timeout_seconds": 300
                    },
                    {
                        "name": "data_processor",
                        "script_name": "data_processor_script",
                        "params": {"algorithm": "ml"},
                        "max_retries": 3,
                        "timeout_seconds": 600
                    }
                ],
                "edges": [
                    {
                        "from_node": "data_loader",
                        "to_node": "data_processor",
                        "condition_type": "success"
                    }
                ],
                "triggers": [
                    {
                        "trigger_type": "manual",
                        "config": {},
                        "is_active": True
                    }
                ]
            }
        }

# 2. Workflow Oluşturma - Giden/Response
class WorkflowCreateResponse(BaseModel):
    success: bool = Field(..., description="Operation success status")
    workflow_id: str = Field(..., description="Generated workflow UUID")
    workflow_name: str = Field(..., description="Workflow name")
    nodes_created: int = Field(..., description="Number of nodes created")
    edges_created: int = Field(..., description="Number of edges created")
    triggers_created: int = Field(..., description="Number of triggers created")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "workflow_id": "550e8400-e29b-41d4-a716-446655440000",
                "workflow_name": "data_processing_workflow",
                "nodes_created": 2,
                "edges_created": 1,
                "triggers_created": 1
            }
        }

# 3. Workflow Silme - Gelen/Request 
class WorkflowDeleteRequest(BaseModel):
    workflow_id: str = Field(..., description="Workflow UUID to delete")
    
    class Config:
        json_schema_extra = {
            "example": {
                "workflow_id": "550e8400-e29b-41d4-a716-446655440000"
            }
        }

# 4. Workflow Silme - Giden/Response
class WorkflowDeleteReponse(BaseModel):
    success: bool = Field(..., description="Operation success status")
    workflow_id: str = Field(..., description="Deleted workflow UUID")
    workflow_name: str = Field(..., description="Deleted workflow name")
    message: str = Field(..., description="Operation result message")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "workflow_id": "550e8400-e29b-41d4-a716-446655440000",
                "workflow_name": "data_processing_workflow",
                "message": "Workflow and all components deleted successfully"
            }
        }

# 5. Workflow Güncelleme - Gelen/Request 
class WorkflowUpdateRequest(BaseModel):
    workflow_id: str = Field(..., description="Workflow UUID to update")
    name: Optional[str] = Field(None, description="New workflow name")
    description: Optional[str] = Field(None, description="New workflow description")
    nodes: Optional[List[Dict[str, Any]]] = Field(None, description="New list of workflow nodes")
    edges: Optional[List[Dict[str, Any]]] = Field(None, description="New list of workflow edges")
    triggers: Optional[List[Dict[str, Any]]] = Field(None, description="New list of workflow triggers")
    
    class Config:
        json_schema_extra = {
            "example": {
                "workflow_id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "updated_data_processing_workflow",
                "description": "Updated workflow description",
                "nodes": [
                    {
                        "name": "updated_data_loader",
                        "script_name": "data_loader_script",
                        "params": {"source": "database"},
                        "max_retries": 5,
                        "timeout_seconds": 400
                    }
                ],
                "edges": [
                    {
                        "from_node": "updated_data_loader",
                        "to_node": "data_processor",
                        "condition_type": "success"
                    }
                ],
                "triggers": [
                    {
                        "trigger_type": "schedule",
                        "config": {"cron": "0 0 * * *"},
                        "is_active": True
                    }
                ]
            }
        }

# 6. Workflow Güncelleme - Giden/Response
class WorkflowUpdateReponse(BaseModel):
    success: bool = Field(..., description="Operation success status")
    operation: str = Field(..., description="Type of operation performed")
    old_workflow: Dict[str, Any] = Field(..., description="Old workflow information")
    new_workflow: Dict[str, Any] = Field(..., description="New workflow information")
    components_created: Dict[str, int] = Field(..., description="Number of components created")
    message: str = Field(..., description="Operation result message")
    warning: str = Field(..., description="Warning message about ID change")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "operation": "update_via_delete_create",
                "old_workflow": {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "name": "data_processing_workflow",
                    "status": "deleted"
                },
                "new_workflow": {
                    "id": "660e8400-e29b-41d4-a716-446655440000",
                    "name": "updated_data_processing_workflow",
                    "status": "created"
                },
                "components_created": {
                    "nodes": 1,
                    "edges": 1,
                    "triggers": 1
                },
                "message": "Workflow updated successfully - old workflow 'data_processing_workflow' deleted, new workflow 'updated_data_processing_workflow' created",
                "warning": "Workflow ID changed because workflow was completely recreated"
            }
        }

# 7. Workflow Listeleme - Giden/Response
class WorkflowListResponse(BaseModel):
    workflow_id: str = Field(..., description="Workflow UUID")
    name: str = Field(..., description="Workflow name")
    description: Optional[str] = Field(None, description="Workflow description")
    status: str = Field(..., description="Workflow status")
    priority: int = Field(..., description="Workflow priority")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "workflow_id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "data_processing_workflow",
                "description": "Process data through multiple stages",
                "status": "active",
                "priority": 0,
                "created_at": "2024-01-01T12:00:00",
                "updated_at": "2024-01-01T12:00:00"
            }
        }

# 8. Workflow Detay - Giden/Response
class WorkflowGetResponse(BaseModel):
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
    
    class Config:
        json_schema_extra = {
            "example": {
                "workflow_id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "data_processing_workflow",
                "description": "Process data through multiple stages",
                "status": "active",
                "priority": 0,
                "created_at": "2024-01-01T12:00:00",
                "updated_at": "2024-01-01T12:00:00",
                "nodes": [
                    {
                        "node_id": "node-1",
                        "name": "data_loader",
                        "script_name": "data_loader_script",
                        "params": {"source": "file"},
                        "max_retries": 3,
                        "timeout_seconds": 300
                    }
                ],
                "edges": [
                    {
                        "edge_id": "edge-1",
                        "from_node": "data_loader",
                        "to_node": "data_processor",
                        "condition_type": "success"
                    }
                ],
                "triggers": [
                    {
                        "trigger_id": "trigger-1",
                        "trigger_type": "manual",
                        "config": {},
                        "is_active": True
                    }
                ]
            }
        }