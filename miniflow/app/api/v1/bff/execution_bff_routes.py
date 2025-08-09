from fastapi import APIRouter, Depends

# Request/Response Schemas
from miniflow.app.schemas.v1 import (
    ExecutionSearchRequest, ExecutionCancelRequest
)
from miniflow.app.schemas.v1 import (
    ExecutionListResponse, ExecutionDetailResponse, ExecutionResultsResponse,
    ExecutionStatusResponse, ExecutionCancelResponse, ExecutionSearchResponse, 
    ExecutionCountResponse, ExecutionExistsResponse
)

# Services
from miniflow.app.services import ExecutionService
from miniflow.app.dependencies import get_execution_service


router = APIRouter()

# ===================================================================================================  EXECUTION CREATE  ==
@router.post("/create", response_model=ExecutionDetailResponse)
async def api_execution_create(execution_data: dict, execution_service: ExecutionService = Depends(get_execution_service)):
    """Yeni execution oluştur"""
    result = await execution_service.execution_create(execution_data)
    return ExecutionDetailResponse(**result)

# ===================================================================================================  EXECUTION UPDATE  ==
@router.post("/{execution_id}/update", response_model=ExecutionDetailResponse)
async def api_execution_update(execution_id: str, execution_data: dict, execution_service: ExecutionService = Depends(get_execution_service)):
    """Execution'ı güncelle"""
    result = await execution_service.execution_update(execution_id, execution_data)
    return ExecutionDetailResponse(**result)

# ===================================================================================================  EXECUTION DELETE  ==
@router.post("/{execution_id}/delete", response_model=ExecutionCancelResponse)
async def api_execution_delete(execution_id: str, force: bool = False, execution_service: ExecutionService = Depends(get_execution_service)):
    """Execution'ı sil"""
    result = await execution_service.execution_delete(execution_id, force)
    return ExecutionCancelResponse(**result)

# =================================================================================================  EXECUTION VALIDATE  ==
@router.post("/{execution_id}/validate", response_model=ExecutionStatusResponse)
async def api_execution_validate(execution_id: str, execution_service: ExecutionService = Depends(get_execution_service)):
    """Execution'ı doğrula"""
    result = await execution_service.execution_validate(execution_id)
    return ExecutionStatusResponse(**result)

# ===================================================================================================  EXECUTION SEARCH  ==
@router.post("/search", response_model=ExecutionSearchResponse)
async def api_execution_search(filter_data: ExecutionSearchRequest, execution_service: ExecutionService = Depends(get_execution_service)):
    """Execution'ları filtrele"""
    result = await execution_service.execution_search(filter_data.model_dump())
    return ExecutionSearchResponse(**result)

# =====================================================================================================  EXECUTION LIST  ==
@router.get("/", response_model=ExecutionListResponse)
async def api_execution_list(execution_service: ExecutionService = Depends(get_execution_service)):
    """Tüm execution'ları listele"""
    result = await execution_service.execution_list()
    return ExecutionListResponse(**result)

# ======================================================================================================  EXECUTION GET  ==
@router.get("/{execution_id}", response_model=ExecutionDetailResponse)
async def api_execution_get(execution_id: str, execution_service: ExecutionService = Depends(get_execution_service)):
    """Execution detaylarını getir"""
    result = await execution_service.execution_get(execution_id)
    return ExecutionDetailResponse(**result)

# ====================================================================================================  EXECUTION COUNT  ==
@router.get("/count", response_model=ExecutionCountResponse)
async def api_execution_count(execution_service: ExecutionService = Depends(get_execution_service)):
    """Execution sayısını getir"""
    result = await execution_service.execution_count()
    return ExecutionCountResponse(**result)

# ===================================================================================================  EXECUTION EXISTS  ==
@router.get("/{execution_id}/exists", response_model=ExecutionExistsResponse)
async def api_execution_exists(execution_id: str, execution_service: ExecutionService = Depends(get_execution_service)):
    """Execution'ın var olup olmadığını kontrol et"""
    result = await execution_service.execution_exists(execution_id)
    return ExecutionExistsResponse(**result)

# =================================================================================================  EXECUTION RESULTS  ==
@router.get("/{execution_id}/results", response_model=ExecutionResultsResponse)
async def api_execution_results(execution_id: str, execution_service: ExecutionService = Depends(get_execution_service)):
    """Execution sonuçlarını getir"""
    result = await execution_service.execution_results(execution_id)
    return ExecutionResultsResponse(**result)

# =================================================================================================  EXECUTION STATUS  ==
@router.get("/{execution_id}/status", response_model=ExecutionStatusResponse)
async def api_execution_status(execution_id: str, execution_service: ExecutionService = Depends(get_execution_service)):
    """Execution durumunu getir"""
    result = await execution_service.execution_status(execution_id)
    return ExecutionStatusResponse(**result)

# =================================================================================================  EXECUTION CANCEL  ==
@router.post("/{execution_id}/cancel", response_model=ExecutionCancelResponse)
async def api_execution_cancel(execution_id: str, cancel_data: ExecutionCancelRequest, execution_service: ExecutionService = Depends(get_execution_service)):
    """Execution'ı iptal et"""
    result = await execution_service.execution_cancel(execution_id, cancel_data.model_dump())
    return ExecutionCancelResponse(**result)