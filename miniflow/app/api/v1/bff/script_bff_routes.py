from fastapi import APIRouter, Depends, Query

# Request/Response Schemas
from miniflow.app.schemas.v1 import (
    ScriptCreateRequest, ScriptUpdateRequest, ScriptSearchRequest, ScriptTestRequest
)
from miniflow.app.schemas.v1 import (
    ScriptListResponse, ScriptDetailResponse, ScriptCreateResponse, ScriptUpdateResponse,
    ScriptDeleteResponse, ScriptTestResponse, ScriptSearchResponse, ScriptCountResponse, 
    ScriptExistsResponse, ScriptValidateResponse
)

# Services
from miniflow.app.services import ScriptService
from miniflow.app.dependencies import get_script_service


router = APIRouter()

# =====================================================================================================  SCRIPT CREATE  ==
@router.post("/create", response_model=ScriptCreateResponse)
async def api_script_create(script_data: ScriptCreateRequest, script_service: ScriptService = Depends(get_script_service)):
    """Yeni script oluştur"""
    result = await script_service.script_create(script_data.model_dump())
    return ScriptCreateResponse(**result)

# =====================================================================================================  SCRIPT UPDATE  ==
@router.post("/{script_id}/update", response_model=ScriptUpdateResponse)
async def api_script_update(script_id: str, script_data: ScriptUpdateRequest, script_service: ScriptService = Depends(get_script_service)):
    """Script'i güncelle"""
    result = await script_service.script_update(script_id, script_data.model_dump(exclude_unset=True))
    return ScriptUpdateResponse(**result)

# =====================================================================================================  SCRIPT DELETE  ==
@router.post("/{script_id}/delete", response_model=ScriptDeleteResponse)
async def api_script_delete(script_id: str, force: bool = False, script_service: ScriptService = Depends(get_script_service)):
    """Script'i sil"""
    result = await script_service.script_delete(script_id, force)
    return ScriptDeleteResponse(**result)

# ===================================================================================================  SCRIPT VALIDATE  ==
@router.post("/{script_id}/validate", response_model=ScriptValidateResponse)
async def api_script_validate(script_id: str, script_service: ScriptService = Depends(get_script_service)):
    """Script'i doğrula"""
    result = await script_service.script_validate(script_id)
    return ScriptValidateResponse(**result)

# =====================================================================================================  SCRIPT SEARCH  ==
@router.post("/search", response_model=ScriptSearchResponse)
async def api_script_search(filter_data: ScriptSearchRequest, script_service: ScriptService = Depends(get_script_service)):
    """Script'leri filtrele"""
    result = await script_service.script_search(filter_data.model_dump())
    return ScriptSearchResponse(**result)

# =======================================================================================================  SCRIPT LIST  ==
@router.get("/", response_model=ScriptListResponse)
async def api_script_list(
    language: str = None,
    test_status: str = None,
    page: int = None,
    page_size: int = None,
    script_service: ScriptService = Depends(get_script_service)
):
    """Tüm script'leri listele"""
    result = await script_service.script_list(language=language, test_status=test_status, page=page, page_size=page_size)
    return ScriptListResponse(**result)

# ========================================================================================================  SCRIPT GET  ==
@router.get("/{script_id}", response_model=ScriptDetailResponse)
async def api_script_get(script_id: str, include_content: bool = Query(False), script_service: ScriptService = Depends(get_script_service)):
    """Script detaylarını getir"""
    result = await script_service.script_get(script_id, include_content)
    return ScriptDetailResponse(**result)

# ======================================================================================================  SCRIPT COUNT  ==
@router.get("/count", response_model=ScriptCountResponse)
async def api_script_count(
    group_by: str = None,
    script_service: ScriptService = Depends(get_script_service)
):
    """Script sayısını getir (total, by language, by test_status, etc.)"""
    result = await script_service.script_count(group_by=group_by)
    return ScriptCountResponse(**result)

# =====================================================================================================  SCRIPT EXISTS  ==
@router.get("/{script_id}/exists", response_model=ScriptExistsResponse)
async def api_script_exists(script_id: str, script_service: ScriptService = Depends(get_script_service)):
    """Script'in var olup olmadığını kontrol et"""
    result = await script_service.script_exists(script_id)
    return ScriptExistsResponse(**result)

# =====================================================================================================  SCRIPT TEST  ==
@router.post("/{script_id}/test", response_model=ScriptTestResponse)
async def api_script_test(script_id: str, test_data: ScriptTestRequest, script_service: ScriptService = Depends(get_script_service)):
    """Script'i test et"""
    result = await script_service.script_test(script_id, test_data.model_dump())
    return ScriptTestResponse(**result)