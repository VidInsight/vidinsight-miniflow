from fastapi import APIRouter, Depends

# Request/Response Schemas
from miniflow.app.schemas.v1 import (
    NodeCreateRequest, NodeUpdateRequest, NodeSearchRequest
)
from miniflow.app.schemas.v1 import (
    NodeListResponse, NodeDetailResponse, NodeCreateResponse, NodeUpdateResponse,
    NodeDeleteResponse, NodeValidateResponse, NodeSearchResponse, NodeCountResponse, NodeExistsResponse
)

# Services
from miniflow.app.services import NodeService
from miniflow.app.dependencies import get_node_service


router = APIRouter()

# =====================================================================================================  NODE CREATE  ==
@router.post("/create", response_model=NodeCreateResponse)
async def api_node_create(node_data: NodeCreateRequest, node_service: NodeService = Depends(get_node_service)):
    """Yeni node oluştur"""
    result = await node_service.node_create(node_data.model_dump())
    return NodeCreateResponse(**result)

# =====================================================================================================  NODE UPDATE  ==
@router.post("/{node_id}/update", response_model=NodeUpdateResponse)
async def api_node_update(node_id: str, node_data: NodeUpdateRequest, node_service: NodeService = Depends(get_node_service)):
    """Node'u güncelle"""
    result = await node_service.node_update(node_id, node_data.model_dump(exclude_unset=True))
    return NodeUpdateResponse(**result)

# =====================================================================================================  NODE DELETE  ==
@router.post("/{node_id}/delete", response_model=NodeDeleteResponse)
async def api_node_delete(node_id: str, force: bool = False, node_service: NodeService = Depends(get_node_service)):
    """Node'u sil"""
    result = await node_service.node_delete(node_id, force)
    return NodeDeleteResponse(**result)

# ===================================================================================================  NODE VALIDATE  ==
@router.post("/{node_id}/validate", response_model=NodeValidateResponse)
async def api_node_validate(node_id: str, node_service: NodeService = Depends(get_node_service)):
    """Node'u doğrula"""
    result = await node_service.node_validate(node_id)
    return NodeValidateResponse(**result)

# =====================================================================================================  NODE SEARCH  ==
@router.post("/search", response_model=NodeSearchResponse)
async def api_node_search(filter_data: NodeSearchRequest, node_service: NodeService = Depends(get_node_service)):
    """Node'ları filtrele"""
    result = await node_service.node_search(filter_data.model_dump())
    return NodeSearchResponse(**result)

# =======================================================================================================  NODE LIST  ==
@router.get("/", response_model=NodeListResponse)
async def api_node_list(node_service: NodeService = Depends(get_node_service)):
    """Tüm node'ları listele"""
    result = await node_service.node_list()
    return NodeListResponse(**result)

# ========================================================================================================  NODE GET  ==
@router.get("/{node_id}", response_model=NodeDetailResponse)
async def api_node_get(node_id: str, node_service: NodeService = Depends(get_node_service)):
    """Node detaylarını getir"""
    result = await node_service.node_get(node_id)
    return NodeDetailResponse(**result)

# ======================================================================================================  NODE COUNT  ==
@router.get("/count", response_model=NodeCountResponse)
async def api_node_count(node_service: NodeService = Depends(get_node_service)):
    """Node sayısını getir"""
    result = await node_service.node_count()
    return NodeCountResponse(**result)

# =====================================================================================================  NODE EXISTS  ==
@router.get("/{node_id}/exists", response_model=NodeExistsResponse)
async def api_node_exists(node_id: str, node_service: NodeService = Depends(get_node_service)):
    """Node'un var olup olmadığını kontrol et"""
    result = await node_service.node_exists(node_id)
    return NodeExistsResponse(**result)