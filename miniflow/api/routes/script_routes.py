from fastapi import APIRouter, status, HTTPException, Depends, Query
from typing import List, Optional
import logging
import os

from ..models import (
    ScriptCreateRequest, ScriptCreateResponse, 
    ScriptDeleteRequest, ScriptDeleteReponse, 
    ScriptListResponse, ScriptGetResponse,
    )

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/scripts", tags=["SCRIPTS"])


# MiniflowCore instance'ına erişim için dependency
def get_miniflow_core():
    from .. import miniflow_core
    return miniflow_core


@router.post("/create", response_model=ScriptCreateResponse, status_code=status.HTTP_201_CREATED)
async def script_create(request: ScriptCreateRequest, core = Depends(get_miniflow_core)):
    try:
        # Request verilerini hazırla
        script_data = {
            'name': request.name,
            'description': request.description,
            'input_structure': request.input_structure,
            'output_structure': request.output_structure
        }
        
        # MiniflowCore'dan script oluştur (güncellenmiş method)
        result = core.script_create(
            script_data=script_data, 
            script_content=request.file_content
        )
        
        response_data = {
            'script_id': result['id'],
            'name': result['name'],
            'description': result['description'] or '',
            'absolute_path': result['script_path'],
            'language': result['language'],
            'input_structure': result['input_params'],
            'output_structure': result['output_params'],
            'test_status': result['test_status'],
            'created_at': result['created_at']
        }
        
        # Response model'e uygun formatta döndür
        return ScriptCreateResponse(**response_data)
        
    except ValueError as e:
        logger.error(f"Script creation validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Script creation unexpected error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error occurred while creating script"
        )


@router.post("/delete", response_model=ScriptDeleteReponse, status_code=status.HTTP_202_ACCEPTED)
async def script_delete(request: ScriptDeleteRequest, core = Depends(get_miniflow_core)):
    try:
        result = core.script_delete(request.script_id)
        
        response_data = {
            'success': result['success'],
            'script_id': result['script_id'],
            'script_name': result['script_name'],
            'message': result['message']
        }
        
        return ScriptDeleteReponse(**response_data)
        
    except ValueError as e:
        logger.error(f"Script deletion validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Script deletion unexpected error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error occurred while deleting script"
        )


@router.get("/list", response_model=List[ScriptListResponse])
async def script_list(core = Depends(get_miniflow_core)):
    try:
        scripts = core.script_list()
        
        response_data = []
        for script in scripts:
            response_data.append({
                'script_id': script['id'],
                'name': script['name'],
                'description': script['description'],
                'language': script['language'],
                'test_status': script['test_status'],
                'created_at': script['created_at'],
                'updated_at': script['updated_at']
            })
        
        return [ScriptListResponse(**script_data) for script_data in response_data]
        
    except Exception as e:
        logger.error(f"Script listing unexpected error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error occurred while listing scripts"
        )


@router.get("/{script_id}", response_model=ScriptGetResponse)
async def script_get(script_id: str, include_content: bool = Query(False, description="Include script file content in response"),core = Depends(get_miniflow_core)):
    try:
        result = core.script_get(script_id, include_content)
        
        response_data = {
            'script_id': result['id'],
            'name': result['name'],
            'description': result['description'],
            'absolute_path': result['script_path'],
            'language': result['language'],
            'input_structure': result['input_params'],
            'output_structure': result['output_params'],
            'test_status': result['test_status'],
            'created_at': result['created_at'],
            'updated_at': result['updated_at'],
            'file_content': result.get('file_content')
        }
        
        return ScriptGetResponse(**response_data)
        
    except ValueError as e:
        logger.error(f"Script get validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Script get unexpected error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error occurred while retrieving script"
        )
