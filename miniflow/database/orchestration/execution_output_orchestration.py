# orchestration/execution_output_orchestration.py
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, Union, List
from datetime import datetime, timezone

from .base_orchestration import BaseOrchestration
from ...exceptions import ValidationError, BusinessLogicError


class ExecutionOutputOrchestrator(BaseOrchestration):
    """Execution Output operasyonları için orchestrator"""

    def __init__(self):
        super().__init__()
  
    def get_all(self, session: Session) -> List[Dict[str, Any]]:
        """Tüm execution output'ları getir"""
        execution_outputs = self.execution_output_crud.get_all(session)
        return [execution_output.to_dict() for execution_output in execution_outputs]
        
    def search(self, session: Session, search_criteria: Dict[str, Any], skip: int = 0, limit: int = 100, order_by_field: str = None) -> Dict[str, Any]:
        """Execution output arama"""
        # 1. OPERATION: Search execution outputs
        execution_outputs = self.execution_output_crud.filter(session, search_criteria, skip=skip, limit=limit, order_by_field=order_by_field)
        
        # Get total count for pagination
        total_count = self.execution_output_crud.count_filtered(session, search_criteria)
        
        # 2. RETURN: API Format
        return {
            'data': [execution_output.to_dict() for execution_output in execution_outputs],
            'total_count': total_count,
            'skip': skip,
            'limit': limit,
            'has_more': (skip + limit) < total_count
        }
        
    def get(self, session: Session, execution_output_id: str) -> Dict[str, Any]:
        """Execution output detayını getir"""
        # 1. VALIDATION: Execution Output ID
        execution_output = self.execution_output_crud.find_by_id(session, execution_output_id)
        if not execution_output:
            raise BusinessLogicError(f"Execution output not found: {execution_output_id}")

        # 2. RETURN: API Format
        return execution_output.to_dict()

    def count(self, session: Session) -> int:
        """Execution output sayısını getir"""
        return self.execution_output_crud.count(session)
    
    def exists(self, session: Session, execution_output_id: str) -> bool:
        """Execution output var mı kontrolü"""
        return self.execution_output_crud.exists(session, execution_output_id)

    def get_by_execution(self, session: Session, execution_id: str) -> List[Dict[str, Any]]:
        """Belirli bir execution'a ait execution output'ları getir"""
        # 1. OPERATION: Get execution outputs by execution
        execution_outputs = self.execution_output_crud.get_by_execution(session, execution_id)
        return [execution_output.to_dict() for execution_output in execution_outputs]

    def get_by_node(self, session: Session, node_id: str) -> List[Dict[str, Any]]:
        """Belirli bir node'a ait execution output'ları getir"""
        # 1. OPERATION: Get execution outputs by node
        execution_outputs = self.execution_output_crud.filter(session, {'node_id': node_id})
        return [execution_output.to_dict() for execution_output in execution_outputs]

    def get_by_status(self, session: Session, status: str) -> List[Dict[str, Any]]:
        """Belirli bir status'a sahip execution output'ları getir"""
        # 1. VALIDATION: Status
        if not status:
            raise ValidationError("Status is required")
            
        # 2. OPERATION: Get execution outputs by status
        execution_outputs = self.execution_output_crud.filter(session, {'status': status})
        return [execution_output.to_dict() for execution_output in execution_outputs]