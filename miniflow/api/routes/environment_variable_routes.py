from fastapi import APIRouter, status, HTTPException, Depends, Query
from typing import List, Optional
import logging

from ..models import (
    EnvironmentVariableCreateRequest, EnvironmentVariableCreateResponse,
    EnvironmentVariableUpdateRequest, EnvironmentVariableUpdateResponse,
    EnvironmentVariableDeleteResponse, EnvironmentVariableGetResponse,
    EnvironmentVariableListResponse
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/environment-variables", tags=["ENVIRONMENT VARIABLES"])

# MiniflowCore instance'ına erişim için dependency
def get_miniflow_core():
    from .. import miniflow_core
    return miniflow_core


@router.post("/create", response_model=EnvironmentVariableCreateResponse, status_code=status.HTTP_201_CREATED)
async def environment_variable_create(env_var_data: EnvironmentVariableCreateRequest, miniflow_core=Depends(get_miniflow_core)):
    """Create a new environment variable"""
    # Convert Pydantic model to dict
    env_var_dict = env_var_data.model_dump()
    
    # Call core method (Exception handling centralized)
    result = miniflow_core.environment_variable_create(env_var_dict)
    
    # Map response
    return EnvironmentVariableCreateResponse(
        env_var_id=result["env_var_id"],
        name=result["name"],
        value=result["value"],
        is_active=result["is_active"],
        created_at=result["created_at"]
    )

@router.get("/list", response_model=EnvironmentVariableListResponse)
async def environment_variable_list(
    active_only: bool = Query(False, description="Only return active environment variables"),
    miniflow_core=Depends(get_miniflow_core)
):
    """List all environment variables"""
    # Call core method (Exception handling centralized)
    env_vars = miniflow_core.environment_variable_list(active_only=active_only)
    
    # Map response to EnvironmentVariableGetResponse format for each variable
    env_var_responses = []
    for env_var in env_vars:
        env_var_responses.append(EnvironmentVariableGetResponse(
            env_var_id=env_var["id"],
            name=env_var["name"],
            value=env_var["value"],
            description=env_var.get("description"),
            is_active=env_var["is_active"],
            created_at=env_var["created_at"],
            updated_at=env_var["updated_at"]
        ))
    
    return EnvironmentVariableListResponse(environment_variables=env_var_responses)

@router.get("/{env_var_id}", response_model=EnvironmentVariableGetResponse)
async def environment_variable_get(env_var_id: str, miniflow_core=Depends(get_miniflow_core)):
    """Get environment variable details by ID"""
    # Call core method (Exception handling centralized)
    env_var = miniflow_core.environment_variable_get(env_var_id)
    
    # Map response
    return EnvironmentVariableGetResponse(
        env_var_id=env_var["id"],
        name=env_var["name"],
        value=env_var["value"],
        description=env_var.get("description"),
        is_active=env_var["is_active"],
        created_at=env_var["created_at"],
        updated_at=env_var["updated_at"]
    )

@router.get("/name/{name}", response_model=EnvironmentVariableGetResponse)
async def environment_variable_get_by_name(name: str, miniflow_core=Depends(get_miniflow_core)):
    """Get environment variable details by name"""
    # Call core method (Exception handling centralized)
    env_var = miniflow_core.environment_variable_get_by_name(name)
    
    # Map response
    return EnvironmentVariableGetResponse(
        env_var_id=env_var["id"],
        name=env_var["name"],
        value=env_var["value"],
        description=env_var.get("description"),
        is_active=env_var["is_active"],
        created_at=env_var["created_at"],
        updated_at=env_var["updated_at"]
    )

@router.put("/update/{env_var_id}", response_model=EnvironmentVariableUpdateResponse, status_code=status.HTTP_200_OK)
async def environment_variable_update(
    env_var_id: str, 
    env_var_data: EnvironmentVariableUpdateRequest, 
    miniflow_core=Depends(get_miniflow_core)
):
    """Update an existing environment variable"""
    # Convert Pydantic model to dict
    env_var_dict = env_var_data.model_dump(exclude_unset=True)
    
    # Call core method (Exception handling centralized)
    result = miniflow_core.environment_variable_update(env_var_id, env_var_dict)
    
    # Map response
    return EnvironmentVariableUpdateResponse(
        env_var_id=result["env_var_id"],
        name=result["name"],
        value=result["value"],
        is_active=result["is_active"],
        updated_at=result["updated_at"]
    )

@router.post("/activate/{env_var_id}", status_code=status.HTTP_200_OK)
async def environment_variable_activate(env_var_id: str, miniflow_core=Depends(get_miniflow_core)):
    """Activate an environment variable"""
    # Call core method (Exception handling centralized)
    result = miniflow_core.environment_variable_activate(env_var_id)
    
    return {
        "message": f"Environment variable '{result['name']}' activated successfully",
        "env_var_id": result["env_var_id"],
        "is_active": result["is_active"]
    }

@router.post("/deactivate/{env_var_id}", status_code=status.HTTP_200_OK)
async def environment_variable_deactivate(env_var_id: str, miniflow_core=Depends(get_miniflow_core)):
    """Deactivate an environment variable"""
    # Call core method (Exception handling centralized)
    result = miniflow_core.environment_variable_deactivate(env_var_id)
    
    return {
        "message": f"Environment variable '{result['name']}' deactivated successfully",
        "env_var_id": result["env_var_id"],
        "is_active": result["is_active"]
    }

@router.delete("/delete/{env_var_id}", response_model=EnvironmentVariableDeleteResponse, status_code=status.HTTP_200_OK)
async def environment_variable_delete(env_var_id: str, miniflow_core=Depends(get_miniflow_core)):
    """Delete an existing environment variable"""
    # Call core method (Exception handling centralized)
    result = miniflow_core.environment_variable_delete(env_var_id)
    
    # Map response
    return EnvironmentVariableDeleteResponse(
        env_var_id=result["env_var_id"],
        name=result["name"]
    ) 