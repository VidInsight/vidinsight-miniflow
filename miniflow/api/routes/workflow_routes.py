from fastapi import APIRouter, status
from typing import List, Optional
from fastapi import APIRouter, status, HTTPException, Depends, Query
from typing import List, Optional
import logging

from ..models import (
    WorkflowCreateRequest, WorkflowCreateResponse,
    WorkflowDeleteRequest, WorkflowDeleteReponse,
    WorkflowUpdateRequest, WorkflowUpdateReponse,
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
    try:
        # Convert Pydantic model to dict
        workflow_dict = workflow_data.model_dump()
        
        # Call core method
        result = miniflow_core.workflow_create(workflow_dict)
        
        # Map response
        return WorkflowCreateResponse(
            success=result["success"],
            workflow_id=result["workflow_dict"]["id"],
            workflow_name=result["workflow_name"],
            nodes_created=result["nodes_created"],
            edges_created=result["edges_created"],
            triggers_created=result["triggers_created"]
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Workflow creation error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

@router.post("/update", response_model=WorkflowUpdateReponse, status_code=status.HTTP_202_ACCEPTED)
async def workflow_update(workflow_data: WorkflowUpdateRequest, miniflow_core=Depends(get_miniflow_core)):
    """Update an existing workflow"""
    try:
        # Convert Pydantic model to dict, excluding workflow_id
        workflow_dict = workflow_data.model_dump(exclude={'workflow_id'})
        
        # Call core method
        result = miniflow_core.workflow_update(workflow_data.workflow_id, workflow_dict)
        
        # Map response
        return WorkflowUpdateReponse(
            success=result["success"],
            operation=result["operation"],
            old_workflow=result["old_workflow"],
            new_workflow=result["new_workflow"],
            components_created=result["components_created"],
            message=result["message"],
            warning=result["warning"]
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Workflow update error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

@router.post("/delete", response_model=WorkflowDeleteReponse, status_code=status.HTTP_202_ACCEPTED)
async def workflow_delete(workflow_data: WorkflowDeleteRequest, miniflow_core=Depends(get_miniflow_core)):
    """Delete an existing workflow"""
    try:
        # Call core method
        result = miniflow_core.workflow_delete(workflow_data.workflow_id)
        
        # Map response
        return WorkflowDeleteReponse(
            success=result["success"],
            workflow_id=result["workflow_id"],
            workflow_name=result["workflow_name"],
            message=result["message"]
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Workflow deletion error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

@router.get("/list", response_model=List[WorkflowListResponse])
async def workflow_list(miniflow_core=Depends(get_miniflow_core)):
    """List all workflows"""
    try:
        # Call core method
        workflows = miniflow_core.workflow_list()
        
        # Map response
        return [
            WorkflowListResponse(
                workflow_id=wf["id"],
                name=wf["name"],
                description=wf.get("description"),
                status=wf["status"],
                priority=wf["priority"],
                created_at=wf["created_at"],
                updated_at=wf["updated_at"]
            )
            for wf in workflows
        ]
    except Exception as e:
        logger.error(f"Workflow list error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

@router.get("/{workflow_id}", response_model=WorkflowGetResponse)
async def workflow_get(workflow_id: str, miniflow_core=Depends(get_miniflow_core)):
    """Get workflow details with nodes, edges, and triggers"""
    try:
        # Call core method
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
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Workflow get error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")