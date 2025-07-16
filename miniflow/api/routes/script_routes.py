from fastapi import APIRouter, status, HTTPException, Depends, Query
from typing import List, Optional
import logging
import os

from ..models import (
    ScriptCreateRequest, ScriptCreateResponse, 
    ScriptDeleteResponse, ScriptGetResponse,
    ScriptListResponse,
    )

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/scripts", tags=["SCRIPTS"])


# MiniflowCore instance'ına erişim için dependency
def get_miniflow_core():
    from .. import miniflow_core
    return miniflow_core


@router.post("/create", response_model=ScriptCreateResponse, status_code=status.HTTP_201_CREATED)
async def script_create(request: ScriptCreateRequest, core = Depends(get_miniflow_core)):
    """Create a new script"""
    # Gelen veriden script
    script_data = {
        'name': request.name,
        'description': request.description,
        'input_params': request.input_params,
        'output_params': request.output_params
    }
    
    # MiniflowCore'dan script oluştur (Exception handling centralized)
    result = core.script_create(
        script_data=script_data, 
        script_content=request.file_content
    )
    
    # Response model'e uygun formatta döndür
    return ScriptCreateResponse(
        script_id=result['script_id'],
        absolute_path=result['absolute_path'],
        created_at=result['created_at']
    )

@router.get("/list", response_model=ScriptListResponse)
async def script_list(core = Depends(get_miniflow_core)):
    """List all scripts"""
    scripts = core.script_list()
    
    script_responses = []
    for script in scripts:
        script_responses.append(ScriptGetResponse(
            script_id=script['id'],
            name=script['name'],
            description=script['description'],
            absolute_path=script['script_path'],
            language=script['language'],
            input_params=script['input_params'],
            output_params=script['output_params'],
            test_status=script['test_status'],
            created_at=script['created_at'],
            updated_at=script['updated_at']
        ))
    
    return ScriptListResponse(scripts=script_responses)

@router.get("/{script_id}", response_model=ScriptGetResponse)
async def script_get(script_id: str, include_content: bool = Query(False, description="Include script file content in response"), core = Depends(get_miniflow_core)):
    """Get script details"""
    result = core.script_get(script_id, include_content)
    
    return ScriptGetResponse(
        script_id=result['id'],  # Fixed: was missing script_id field
        name=result['name'],
        description=result['description'],
        absolute_path=result['script_path'],
        language=result['language'],
        input_params=result['input_params'],
        output_params=result['output_params'],
        test_status=result['test_status'],
        created_at=result['created_at'],
        updated_at=result['updated_at'],
        file_content=result.get('file_content')
    )

@router.post("/delete/{script_id}", response_model=ScriptDeleteResponse, status_code=status.HTTP_202_ACCEPTED)
async def script_delete(script_id: str, core = Depends(get_miniflow_core)):
    """Delete an existing script"""
    result = core.script_delete(script_id)
    
    return ScriptDeleteResponse(
        script_id=result['script_id'],
        script_name=result['script_name']
    )
