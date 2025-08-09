from fastapi import APIRouter, Depends

# Request/Response Schemas (Note: These would need to be created in schemas/v1/env_var_schemas.py)
from miniflow.app.schemas.v1.base_schemas import (
    BaseResponse, DataResponse, CountResponse, ExistsResponse, ListResponse
)

# Services
from miniflow.app.services import EnvVarService
from miniflow.app.dependencies import get_env_var_service


router = APIRouter()

# ===================================================================================================  ENV VAR CREATE  ==
@router.post("/create", response_model=BaseResponse)
async def api_env_var_create(env_var_data: dict, env_var_service: EnvVarService = Depends(get_env_var_service)):
    """Yeni environment variable oluştur"""
    result = await env_var_service.env_var_create(env_var_data)
    return BaseResponse(**result)

# ===================================================================================================  ENV VAR UPDATE  ==
@router.post("/{env_var_id}/update", response_model=BaseResponse)
async def api_env_var_update(env_var_id: str, env_var_data: dict, env_var_service: EnvVarService = Depends(get_env_var_service)):
    """Environment variable'ı güncelle"""
    result = await env_var_service.env_var_update(env_var_id, env_var_data)
    return BaseResponse(**result)

# ===================================================================================================  ENV VAR DELETE  ==
@router.post("/{env_var_id}/delete", response_model=BaseResponse)
async def api_env_var_delete(env_var_id: str, env_var_service: EnvVarService = Depends(get_env_var_service)):
    """Environment variable'ı sil"""
    result = await env_var_service.env_var_delete(env_var_id)
    return BaseResponse(**result)

# =================================================================================================  ENV VAR VALIDATE  ==
@router.post("/{env_var_id}/validate", response_model=BaseResponse)
async def api_env_var_validate(env_var_id: str, env_var_service: EnvVarService = Depends(get_env_var_service)):
    """Environment variable'ı doğrula"""
    result = await env_var_service.env_var_validate(env_var_id)
    return BaseResponse(**result)

# ===================================================================================================  ENV VAR SEARCH  ==
@router.post("/search", response_model=ListResponse)
async def api_env_var_search(search_data: dict, env_var_service: EnvVarService = Depends(get_env_var_service)):
    """Environment variable'ları filtrele"""
    result = await env_var_service.env_var_search(search_data)
    return ListResponse(**result)

# =====================================================================================================  ENV VAR LIST  ==
@router.get("/", response_model=ListResponse)
async def api_env_var_list(env_var_service: EnvVarService = Depends(get_env_var_service)):
    """Tüm environment variable'ları listele"""
    result = await env_var_service.env_var_list()
    return ListResponse(**result)

# ======================================================================================================  ENV VAR GET  ==
@router.get("/{env_var_id}", response_model=DataResponse)
async def api_env_var_get(env_var_id: str, env_var_service: EnvVarService = Depends(get_env_var_service)):
    """Environment variable detaylarını getir"""
    result = await env_var_service.env_var_get(env_var_id)
    return DataResponse(**result)

# ====================================================================================================  ENV VAR COUNT  ==
@router.get("/count", response_model=CountResponse)
async def api_env_var_count(env_var_service: EnvVarService = Depends(get_env_var_service)):
    """Environment variable sayısını getir"""
    result = await env_var_service.env_var_count()
    return CountResponse(**result)

# ===================================================================================================  ENV VAR EXISTS  ==
@router.get("/{env_var_id}/exists", response_model=ExistsResponse)
async def api_env_var_exists(env_var_id: str, env_var_service: EnvVarService = Depends(get_env_var_service)):
    """Environment variable'ın var olup olmadığını kontrol et"""
    result = await env_var_service.env_var_exists(env_var_id)
    return ExistsResponse(**result)

# =================================================================================================  ENV VAR DELETE ALL  ==
@router.post("/delete_all", response_model=BaseResponse)
async def api_env_var_delete_all(env_var_service: EnvVarService = Depends(get_env_var_service)):
    """Tüm environment variable'ları sil"""
    result = await env_var_service.env_var_delete_all()
    return BaseResponse(**result)