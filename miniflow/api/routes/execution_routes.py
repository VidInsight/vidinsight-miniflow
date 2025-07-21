from fastapi import APIRouter, status, HTTPException, Depends, Query
from typing import List, Optional
import logging
import os

from ..models import (
    ExecutionCreateResponse, ExecutionGetResponse, ExecutionCancelResponse,
    ExecutionListResponse
    )

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/executions", tags=["EXECUTIONS"])

# MiniflowCore instance'ına erişim için dependency
def get_miniflow_core():
    from .. import miniflow_core
    return miniflow_core


@router.post("/create/{workflow_id}", response_model=ExecutionCreateResponse, status_code=status.HTTP_201_CREATED)
async def execution_create(workflow_id: str, core = Depends(get_miniflow_core)):
    """Create a new execution by triggering a workflow"""
    result = core.trigger_workflow(workflow_id)

    return ExecutionCreateResponse(
        execution_id=result['execution_id'],
        pending_nodes=result['pending_nodes'],
        pending_nodes_ids=result['pending_nodes_ids'],  # Already IDs now
        started_at=result["started_at"]
    )

@router.post("/cancel/{execution_id}", response_model=ExecutionCancelResponse, status_code=status.HTTP_200_OK)
async def execution_cancel(execution_id: str, core = Depends(get_miniflow_core)):
    """Cancel a running execution"""
    result = core.cancel_execution(execution_id)

    return ExecutionCancelResponse(
        execution_id=result['execution_id'],
        pending_nodes=result['pending_nodes'],
        executed_nodes=result['executed_nodes'],
        results=result['results'],
        started_at=result.get('started_at', '')
    )

@router.get("/list", response_model=ExecutionListResponse, status_code=status.HTTP_200_OK)
async def execution_list(core = Depends(get_miniflow_core)):
    """List all executions"""
    result = core.execution_list()

    executions = []
    for execution in result:
        executions.append(ExecutionGetResponse(
            workflow_id=execution['workflow_id'],
            execution_id=execution['id'],  # Map 'id' field to 'execution_id'
            status=execution['status'],
            pending_nodes=execution['pending_nodes'],
            executed_nodes=execution['executed_nodes'],
            results=execution['results'],
            started_at=execution['started_at'],
            ended_at=execution.get('ended_at')  # Handle optional field
        ))

    return ExecutionListResponse(executions=executions)

@router.get("/{execution_id}", response_model=ExecutionGetResponse, status_code=status.HTTP_200_OK)
async def execution_get(execution_id: str, core = Depends(get_miniflow_core)):
    """Get execution details by execution ID"""
    result = core.execution_get(execution_id)

    return ExecutionGetResponse(
        workflow_id=result['workflow_id'],
        execution_id=result['id'],  # Map 'id' field to 'execution_id'
        status=result['status'],
        pending_nodes=result['pending_nodes'],
        executed_nodes=result['executed_nodes'],
        results=result['results'],
        started_at=result['started_at'],
        ended_at=result.get('ended_at')  # Handle optional field
    )