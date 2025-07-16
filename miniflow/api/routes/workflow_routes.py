from fastapi import APIRouter, status, HTTPException, Depends, Query
from typing import List, Optional
import logging

from ..models import (
    WorkflowCreateRequest, WorkflowCreateResponse,
    WorkflowDeleteResponse,
    WorkflowListResponse, WorkflowGetResponse
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/workflows", tags=["WORKFLOWS"])

# MiniflowCore instance'ına erişim için dependency
def get_miniflow_core():
    from .. import miniflow_core
    return miniflow_core


@router.post("/create", response_model=WorkflowCreateResponse, status_code=status.HTTP_201_CREATED)
async def workflow_create(workflow_data: WorkflowCreateRequest, miniflow_core=Depends(get_miniflow_core)):
    """Create a new workflow with nodes, edges, and triggers"""
    # Convert Pydantic model to dict
    workflow_dict = workflow_data.model_dump()
    
    # Call core method (Exception handling centralized)
    result = miniflow_core.workflow_create(workflow_dict)
    
    # Map response
    return WorkflowCreateResponse(
        workflow_id=result["workflow_id"],
        created_at=result["created_at"],
        nodes=result["nodes"],
        edges=result["edges"],
        triggers=result["triggers"]
    )

@router.get("/list", response_model=WorkflowListResponse)
async def workflow_list(miniflow_core=Depends(get_miniflow_core)):
    """List all workflows"""
    # Call core method (Exception handling centralized)
    workflows = miniflow_core.workflow_list()
    
    # Map response to WorkflowGetResponse format for each workflow
    workflow_responses = []
    for wf in workflows:
        workflow_responses.append(WorkflowGetResponse(
            workflow_id=wf["id"],
            name=wf["name"],
            description=wf.get("description"),
            status=wf["status"],
            priority=wf["priority"],
            created_at=wf["created_at"],
            updated_at=wf["updated_at"],
            nodes=wf.get("nodes", []),
            edges=wf.get("edges", []),
            triggers=wf.get("triggers", [])
        ))
    
    return WorkflowListResponse(workflows=workflow_responses)

@router.get("/{workflow_id}", response_model=WorkflowGetResponse)
async def workflow_get(workflow_id: str, miniflow_core=Depends(get_miniflow_core)):
    """Get workflow details with nodes, edges, and triggers"""
    # Call core method (Exception handling centralized)
    workflow = miniflow_core.workflow_get(workflow_id)
    
    # Map response
    return WorkflowGetResponse(
        workflow_id=workflow["id"],
        name=workflow["name"],
        description=workflow.get("description"),
        status=workflow["status"],
        priority=workflow["priority"],
        created_at=workflow["created_at"],
        updated_at=workflow["updated_at"],
        nodes=workflow.get("nodes", []),
        edges=workflow.get("edges", []),
        triggers=workflow.get("triggers", [])
    )

@router.put("/update/{workflow_id}", response_model=WorkflowCreateResponse, status_code=status.HTTP_200_OK)
async def workflow_update(workflow_id: str, workflow_data: WorkflowCreateRequest, miniflow_core=Depends(get_miniflow_core)):
    """Update an existing workflow"""
    # Convert Pydantic model to dict
    workflow_dict = workflow_data.model_dump()
    
    # Call core method (Exception handling centralized)
    result = miniflow_core.workflow_update(workflow_id, workflow_dict)
    
    # Map response (same format as create)
    return WorkflowCreateResponse(
        workflow_id=result["workflow_id"],
        created_at=result["created_at"],
        nodes=result["nodes"],
        edges=result["edges"],
        triggers=result["triggers"]
    )

@router.delete("/delete/{workflow_id}", response_model=WorkflowDeleteResponse, status_code=status.HTTP_200_OK)
async def workflow_delete(workflow_id: str, miniflow_core=Depends(get_miniflow_core)):
    """Delete an existing workflow"""
    # Call core method (Exception handling centralized)
    result = miniflow_core.workflow_delete(workflow_id)
    
    # Map response
    return WorkflowDeleteResponse(
        workflow_id=result["workflow_id"],
        workflow_name=result["workflow_name"]
    )