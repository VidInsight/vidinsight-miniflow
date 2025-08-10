from fastapi import APIRouter, Depends

# Request/Response Schemas
from miniflow.app.schemas.v1 import (
    EnvVarCreateRequest, EnvVarUpdateRequest, EnvVarSearchRequest
)
from miniflow.app.schemas.v1 import (
    EnvVarListResponse, EnvVarCreateResponse, EnvVarUpdateResponse,
    EnvVarDeleteResponse, EnvVarValidateResponse, EnvVarSearchResponse, EnvVarCountResponse, 
    EnvVarExistsResponse, EnvVarDeleteAllResponse, EnvVarSummary
)

# Services
from miniflow.app.services import EnvVarService
from miniflow.app.dependencies import get_env_var_service


router = APIRouter()

# ===================================================================================================  ENV VAR CREATE  ==
@router.post("/create", response_model=EnvVarCreateResponse)
async def api_env_var_create(env_var_data: EnvVarCreateRequest, env_var_service: EnvVarService = Depends(get_env_var_service)):
    """Yeni environment variable oluştur"""
    result = await env_var_service.env_var_create(env_var_data.model_dump())
    return EnvVarCreateResponse(**result)

# ===================================================================================================  ENV VAR UPDATE  ==
@router.post("/{env_var_id}/update", response_model=EnvVarUpdateResponse)
async def api_env_var_update(env_var_id: str, env_var_data: EnvVarUpdateRequest, env_var_service: EnvVarService = Depends(get_env_var_service)):
    """Environment variable'ı güncelle"""
    result = await env_var_service.env_var_update(env_var_id, env_var_data.model_dump(exclude_unset=True))
    return EnvVarUpdateResponse(**result)

# ===================================================================================================  ENV VAR DELETE  ==
@router.post("/{env_var_id}/delete", response_model=EnvVarDeleteResponse)
async def api_env_var_delete(env_var_id: str, env_var_service: EnvVarService = Depends(get_env_var_service)):
    """Environment variable'ı sil"""
    result = await env_var_service.env_var_delete(env_var_id)
    return EnvVarDeleteResponse(**result)

# =================================================================================================  ENV VAR VALIDATE  ==
@router.post("/{env_var_id}/validate", response_model=EnvVarValidateResponse)
async def api_env_var_validate(env_var_id: str, env_var_service: EnvVarService = Depends(get_env_var_service)):
    """Environment variable'ı doğrula"""
    result = await env_var_service.env_var_validate(env_var_id)
    return EnvVarValidateResponse(**result)

# ===================================================================================================  ENV VAR SEARCH  ==
@router.post("/search", response_model=EnvVarSearchResponse)
async def api_env_var_search(filter_data: EnvVarSearchRequest, env_var_service: EnvVarService = Depends(get_env_var_service)):
    """Environment variable'ları filtrele"""
    result = await env_var_service.env_var_search(filter_data.model_dump())
    return EnvVarSearchResponse(**result)

# ====================================================================================================  ENV VAR COUNT  ==
@router.get("/count", response_model=EnvVarCountResponse)
async def api_env_var_count(
    include_all: bool = None,
    env_var_service: EnvVarService = Depends(get_env_var_service)
):
    """Environment variable sayısını getir"""
    result = await env_var_service.env_var_count(include_all=include_all)
    return EnvVarCountResponse(**result)

# =====================================================================================================  ENV VAR LIST  ==
@router.get("/list", response_model=EnvVarListResponse)
async def api_env_var_list(
    include_all: bool = True,
    page: int = None, 
    page_size: int = None,
    env_var_service: EnvVarService = Depends(get_env_var_service)
):
    """Tüm environment variable'ları listele"""
    result = await env_var_service.env_var_list(include_all=include_all, page=page, page_size=page_size)
    return EnvVarListResponse(**result)

# ======================================================================================================  ENV VAR GET  ==
@router.get("/{env_var_id}", response_model=EnvVarSummary)
async def api_env_var_get(
    env_var_id: str, 
    include_value: bool = False,
    env_var_service: EnvVarService = Depends(get_env_var_service)
):
    """Environment variable detaylarını getir"""
    result = await env_var_service.env_var_get(env_var_id, include_value=include_value)
    return EnvVarSummary(**result)

# ===================================================================================================  ENV VAR EXISTS  ==
@router.get("/{env_var_id}/exists", response_model=EnvVarExistsResponse)
async def api_env_var_exists(env_var_id: str, env_var_service: EnvVarService = Depends(get_env_var_service)):
    """Environment variable'ın var olup olmadığını kontrol et"""
    result = await env_var_service.env_var_exists(env_var_id)
    return EnvVarExistsResponse(**result)

# =================================================================================================  ENV VAR DELETE ALL  ==
@router.post("/delete-all", response_model=EnvVarDeleteAllResponse)
async def api_env_var_delete_all(env_var_service: EnvVarService = Depends(get_env_var_service)):
    """Tüm environment variable'ları sil (tehlikeli operasyon)"""
    result = await env_var_service.env_var_delete_all()
    return EnvVarDeleteAllResponse(**result)