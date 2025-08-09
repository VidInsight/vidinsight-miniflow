from fastapi import APIRouter, Depends

# Request/Response Schemas
from miniflow.app.schemas.v1 import (
    WorkflowCreateRequest, WorkflowUpdateRequest, WorkflowSearchRequest, WorkflowCloneRequest
)
from miniflow.app.schemas.v1 import (
    WorkflowListResponse, WorkflowDetailResponse, WorkflowCreateResponse, WorkflowUpdateResponse,
    WorkflowDeleteResponse, WorkflowValidateResponse, WorkflowRunResponse, WorkflowCloneResponse,
    WorkflowSearchResponse, WorkflowCountResponse, WorkflowExistsResponse, WorkflowDetail
)

# Services
from miniflow.app.services import WorkflowService
from miniflow.app.dependencies import get_workflow_service


router = APIRouter()

# =================================================================================================  WORKFLOW CREATE  ==
@router.post("/create", response_model=WorkflowCreateResponse)
async def api_workflow_create(workflow_data: WorkflowCreateRequest,workflow_service: WorkflowService = Depends(get_workflow_service)):
    result = await workflow_service.workflow_create(workflow_data.model_dump())
    return WorkflowCreateResponse(**result)

# =================================================================================================  WORKFLOW UPDATE  ==
@router.post("/{workflow_id}/update", response_model=WorkflowUpdateResponse)
async def api_workflow_update(workflow_id: str,workflow_data: WorkflowUpdateRequest,workflow_service: WorkflowService = Depends(get_workflow_service)):
    """Workflow'u güncelle"""
    result = await workflow_service.workflow_update(workflow_id, workflow_data.model_dump(exclude_unset=True))
    return WorkflowUpdateResponse(**result)

# =================================================================================================  WORKFLOW DELETE  ==
@router.post("/{workflow_id}/delete", response_model=WorkflowDeleteResponse)
async def api_workflow_delete(workflow_id: str,force: bool = False,workflow_service: WorkflowService = Depends(get_workflow_service)):
    """Workflow'u sil"""
    result = await workflow_service.workflow_delete(workflow_id, force)
    return WorkflowDeleteResponse(**result)

# ===============================================================================================  WORKFLOW VALIDATE  ==
@router.post("/{workflow_id}/validate", response_model=WorkflowValidateResponse)
async def api_workflow_validate(workflow_id: str,workflow_service: WorkflowService = Depends(get_workflow_service)):
    """Workflow'u doğrula"""
    result = await workflow_service.workflow_validate(workflow_id)
    return WorkflowValidateResponse(**result)

# =================================================================================================  WORKFLOW SEARCH  ==
@router.post("/search", response_model=WorkflowSearchResponse)
async def api_workflow_search(filter_data: WorkflowSearchRequest,workflow_service: WorkflowService = Depends(get_workflow_service)):
    """Workflow'ları filtrele"""
    result = await workflow_service.workflow_search(filter_data.model_dump())
    return WorkflowSearchResponse(**result)

# ====================================================================================================  WORKFLOW RUN  ==
@router.post("/{workflow_id}/run", response_model=WorkflowRunResponse)
async def api_workflow_run(workflow_id: str,workflow_service: WorkflowService = Depends(get_workflow_service)):
    """Workflow'u çalıştır"""
    result = await workflow_service.workflow_run(workflow_id)
    return WorkflowRunResponse(**result)

# ==================================================================================================  WORKFLOW CLONE  ==
@router.post("/{workflow_id}/clone", response_model=WorkflowCloneResponse)
async def api_workflow_clone(workflow_id: str,clone_data: WorkflowCloneRequest,workflow_service: WorkflowService = Depends(get_workflow_service)):
    """Workflow'u klonla"""
    result = await workflow_service.workflow_clone(workflow_id, clone_data.model_dump())
    return WorkflowCloneResponse(**result)

# ===================================================================================================  WORKFLOW LIST  ==
@router.get("/", response_model=WorkflowListResponse)
async def api_workflow_list(workflow_service: WorkflowService = Depends(get_workflow_service)):
    """Tüm workflow'ları listele"""
    result = await workflow_service.workflow_list()
    return WorkflowListResponse(**result)

# ====================================================================================================  WORKFLOW GET  ==
@router.get("/{workflow_id}", response_model=WorkflowDetailResponse)
async def api_workflow_get(workflow_id: str, workflow_service: WorkflowService = Depends(get_workflow_service)):
    """Workflow detaylarını getir"""
    result = await workflow_service.workflow_get(workflow_id)
    return WorkflowDetailResponse(**result)

# ==================================================================================================  WORKFLOW COUNT  ==
@router.get("/count", response_model=WorkflowCountResponse)
async def api_workflow_count(workflow_service: WorkflowService = Depends(get_workflow_service)):
    """Workflow sayısını getir"""
    result = await workflow_service.workflow_count()
    return WorkflowCountResponse(**result)

# =================================================================================================  WORKFLOW EXISTS  ==
@router.get("/{workflow_id}/exists", response_model=WorkflowExistsResponse)
async def api_workflow_exists(workflow_id: str,workflow_service: WorkflowService = Depends(get_workflow_service)):
    """Workflow'un var olup olmadığını kontrol et (name ile)"""
    result = await workflow_service.workflow_exists(workflow_id)
    return WorkflowExistsResponse(**result)