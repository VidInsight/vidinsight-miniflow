from fastapi import APIRouter, Depends

# Request/Response Schemas
from miniflow.app.schemas.v1 import (
    EdgeCreateRequest, EdgeUpdateRequest, EdgeSearchRequest
)
from miniflow.app.schemas.v1 import (
    EdgeListResponse, EdgeDetailResponse, EdgeCreateResponse, EdgeUpdateResponse,
    EdgeDeleteResponse, EdgeValidateResponse, EdgeSearchResponse, EdgeCountResponse, EdgeExistsResponse
)

# Services
from miniflow.app.services import EdgeService
from miniflow.app.dependencies import get_edge_service


router = APIRouter()

# =====================================================================================================  EDGE CREATE  ==
@router.post("/create", response_model=EdgeCreateResponse)
async def api_edge_create(edge_data: EdgeCreateRequest, edge_service: EdgeService = Depends(get_edge_service)):
    """Yeni edge oluştur"""
    result = await edge_service.edge_create(edge_data.model_dump())
    return EdgeCreateResponse(**result)

# =====================================================================================================  EDGE UPDATE  ==
@router.post("/{edge_id}/update", response_model=EdgeUpdateResponse)
async def api_edge_update(edge_id: str, edge_data: EdgeUpdateRequest, edge_service: EdgeService = Depends(get_edge_service)):
    """Edge'i güncelle"""
    result = await edge_service.edge_update(edge_id, edge_data.model_dump(exclude_unset=True))
    return EdgeUpdateResponse(**result)

# =====================================================================================================  EDGE DELETE  ==
@router.post("/{edge_id}/delete", response_model=EdgeDeleteResponse)
async def api_edge_delete(edge_id: str, force: bool = False, edge_service: EdgeService = Depends(get_edge_service)):
    """Edge'i sil"""
    result = await edge_service.edge_delete(edge_id, force)
    return EdgeDeleteResponse(**result)

# ===================================================================================================  EDGE VALIDATE  ==
@router.post("/{edge_id}/validate", response_model=EdgeValidateResponse)
async def api_edge_validate(edge_id: str, edge_service: EdgeService = Depends(get_edge_service)):
    """Edge'i doğrula"""
    result = await edge_service.edge_validate(edge_id)
    return EdgeValidateResponse(**result)

# =====================================================================================================  EDGE SEARCH  ==
@router.post("/search", response_model=EdgeSearchResponse)
async def api_edge_search(filter_data: EdgeSearchRequest, edge_service: EdgeService = Depends(get_edge_service)):
    """Edge'leri filtrele"""
    result = await edge_service.edge_search(filter_data.model_dump())
    return EdgeSearchResponse(**result)

# =======================================================================================================  EDGE LIST  ==
@router.get("/", response_model=EdgeListResponse)
async def api_edge_list(edge_service: EdgeService = Depends(get_edge_service)):
    """Tüm edge'leri listele"""
    result = await edge_service.edge_list()
    return EdgeListResponse(**result)

# ========================================================================================================  EDGE GET  ==
@router.get("/{edge_id}", response_model=EdgeDetailResponse)
async def api_edge_get(edge_id: str, edge_service: EdgeService = Depends(get_edge_service)):
    """Edge detaylarını getir"""
    result = await edge_service.edge_get(edge_id)
    return EdgeDetailResponse(**result)

# ======================================================================================================  EDGE COUNT  ==
@router.get("/count", response_model=EdgeCountResponse)
async def api_edge_count(edge_service: EdgeService = Depends(get_edge_service)):
    """Edge sayısını getir"""
    result = await edge_service.edge_count()
    return EdgeCountResponse(**result)

# =====================================================================================================  EDGE EXISTS  ==
@router.get("/{edge_id}/exists", response_model=EdgeExistsResponse)
async def api_edge_exists(edge_id: str, edge_service: EdgeService = Depends(get_edge_service)):
    """Edge'in var olup olmadığını kontrol et"""
    result = await edge_service.edge_exists(edge_id)
    return EdgeExistsResponse(**result)