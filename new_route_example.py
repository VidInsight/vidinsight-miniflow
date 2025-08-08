# routes/v1/workflow.py - YENİ YAPI
from fastapi import APIRouter, Depends, status
from typing import List

from ...models.workflow import (
    WorkflowCreateRequest, WorkflowCreateResponse,
    WorkflowGetResponse, WorkflowListResponse,
    WorkflowDeleteResponse
)
from ...services.workflow_service import WorkflowService
from ...validators.workflow_validator import WorkflowValidator
from ...routes.dependencies import get_workflow_service

router = APIRouter(prefix="/workflows", tags=["WORKFLOWS"])

@router.post("/", response_model=WorkflowCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    request: WorkflowCreateRequest,
    service: WorkflowService = Depends(get_workflow_service)
):
    """Create a new workflow"""
    # Route sadece HTTP handling yapıyor
    # Business logic service'de
    return await service.create_workflow(request)

@router.get("/", response_model=WorkflowListResponse)
async def list_workflows(
    include_detail: bool = False,
    service: WorkflowService = Depends(get_workflow_service)
):
    """List all workflows"""
    workflows = await service.list_workflows(include_detail)
    return WorkflowListResponse(workflows=workflows)

@router.get("/{workflow_id}", response_model=WorkflowGetResponse)
async def get_workflow(
    workflow_id: str,
    service: WorkflowService = Depends(get_workflow_service)
):
    """Get workflow details"""
    return await service.get_workflow(workflow_id)

@router.put("/{workflow_id}", response_model=WorkflowCreateResponse)
async def update_workflow(
    workflow_id: str,
    request: WorkflowCreateRequest,
    service: WorkflowService = Depends(get_workflow_service)
):
    """Update workflow"""
    return await service.update_workflow(workflow_id, request)

@router.delete("/{workflow_id}", response_model=WorkflowDeleteResponse)
async def delete_workflow(
    workflow_id: str,
    service: WorkflowService = Depends(get_workflow_service)
):
    """Delete workflow"""
    return await service.delete_workflow(workflow_id)

# routes/dependencies.py - SHARED DEPENDENCIES
from fastapi import Depends
from ...main import MiniflowCore
from ...services.workflow_service import WorkflowService
from ...services.script_service import ScriptService
from ...services.execution_service import ExecutionService

def get_miniflow_core() -> MiniflowCore:
    """Get MiniflowCore instance"""
    from ... import miniflow_core
    return miniflow_core

def get_workflow_service(
    core: MiniflowCore = Depends(get_miniflow_core)
) -> WorkflowService:
    """Get WorkflowService instance"""
    return WorkflowService(core)

def get_script_service(
    core: MiniflowCore = Depends(get_miniflow_core)
) -> ScriptService:
    """Get ScriptService instance"""
    return ScriptService(core)

def get_execution_service(
    core: MiniflowCore = Depends(get_miniflow_core)
) -> ExecutionService:
    """Get ExecutionService instance"""
    return ExecutionService(core)
