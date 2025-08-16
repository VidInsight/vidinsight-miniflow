# orchestration/execution_input_orchestration.py
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, Union, List
from datetime import datetime, timezone

from .base_orchestration import BaseOrchestration
from ...exceptions import ValidationError, BusinessLogicError


class ExecutionInputOrchestrator(BaseOrchestration):
    """Execution Input operasyonları için orchestrator"""

    def __init__(self):
        super().__init__()
  
    def get_all(self, session: Session) -> List[Dict[str, Any]]:
        """Tüm execution input'ları getir"""
        execution_inputs = self.execution_input_crud.get_all(session)
        return [execution_input.to_dict() for execution_input in execution_inputs]
        
    def get(self, session: Session, execution_input_id: str, include_details: bool = False) -> Dict[str, Any]:
        """Execution input detayını getir"""
        # 1. VALIDATION: Execution Input ID
        execution_input = self.execution_input_crud.find_by_id(session, execution_input_id)
        if not execution_input:
            raise BusinessLogicError(f"Execution input not found: {execution_input_id}")

        # 2. OPERATION: Get base execution input data
        execution_input_dict = execution_input.to_dict()
        
        # 3. OPERATION: Add enhanced details if requested
        if include_details:
            # Add execution info
            execution = self.execution_crud.find_by_id(session, execution_input.execution_id)
            execution_input_dict['execution_status'] = execution.status.value if execution else None
            
            # Add workflow info
            workflow = self.workflow_crud.find_by_id(session, execution_input.workflow_id)
            execution_input_dict['workflow_name'] = workflow.name if workflow else None
            
            # Add node info
            node = self.node_crud.find_by_id(session, execution_input.node_id)
            if node:
                execution_input_dict['node_name'] = node.name
                execution_input_dict['node_description'] = node.description
                # Add script info if node has script
                if node.script_id:
                    script = self.script_crud.find_by_id(session, node.script_id)
                    if script:
                        execution_input_dict['script_name'] = script.name
                        execution_input_dict['script_language'] = script.language.value

        # 4. RETURN: API Format
        return execution_input_dict

    def count(self, session: Session) -> int:
        """Execution input sayısını getir"""
        return self.execution_input_crud.count(session)
    
    def exists(self, session: Session, execution_input_id: str) -> bool:
        """Execution input var mı kontrolü"""
        return self.execution_input_crud.exists(session, execution_input_id)

    def search(self, session: Session, search_criteria: Dict[str, Any], skip: int = 0, limit: int = 100, order_by_field: str = None) -> Dict[str, Any]:
        """Execution input arama"""
        # 1. OPERATION: Search execution inputs
        execution_inputs = self.execution_input_crud.filter(session, search_criteria, skip=skip, limit=limit, order_by_field=order_by_field)
        
        # Get total count for pagination
        total_count = self.execution_input_crud.count_filtered(session, search_criteria)
        
        # 2. RETURN: API Format
        return {
            'data': [execution_input.to_dict() for execution_input in execution_inputs],
            'total_count': total_count,
            'skip': skip,
            'limit': limit,
            'has_more': (skip + limit) < total_count
        }

    def get_by_execution(self, session: Session, execution_id: str) -> List[Dict[str, Any]]:
        """Belirli bir execution'a ait execution input'ları getir"""
        # 1. VALIDATION: Execution ID
        execution = self.execution_crud.find_by_id(session, execution_id)
        if not execution:
            raise BusinessLogicError(f"Execution not found: {execution_id}")
        
        # 2. OPERATION: Get execution inputs by execution
        execution_inputs = self.execution_input_crud.get_by_execution(session, execution_id)
        return [execution_input.to_dict() for execution_input in execution_inputs]

    def get_by_workflow(self, session: Session, workflow_id: str) -> List[Dict[str, Any]]:
        """Belirli bir workflow'a ait execution input'ları getir"""
        # 1. VALIDATION: Workflow ID
        workflow = self.workflow_crud.find_by_id(session, workflow_id)
        if not workflow:
            raise BusinessLogicError(f"Workflow not found: {workflow_id}")
        
        # 2. OPERATION: Get execution inputs by workflow
        execution_inputs = self.execution_input_crud.filter(session, {'workflow_id': workflow_id})
        return [execution_input.to_dict() for execution_input in execution_inputs]

    def get_by_node(self, session: Session, node_id: str) -> List[Dict[str, Any]]:
        """Belirli bir node'a ait execution input'ları getir"""
        # 1. VALIDATION: Node ID
        node = self.node_crud.find_by_id(session, node_id)
        if not node:
            raise BusinessLogicError(f"Node not found: {node_id}")
        
        # 2. OPERATION: Get execution inputs by node
        execution_inputs = self.execution_input_crud.filter(session, {'node_id': node_id})
        return [execution_input.to_dict() for execution_input in execution_inputs]

    def get_by_priority(self, session: Session, priority: int) -> List[Dict[str, Any]]:
        """Belirli bir priority'ye sahip execution input'ları getir"""
        # 1. VALIDATION: Priority
        if priority is None or not isinstance(priority, int):
            raise ValidationError("Priority must be an integer")
        
        # 2. OPERATION: Get execution inputs by priority
        execution_inputs = self.execution_input_crud.filter(session, {'priority': priority})
        return [execution_input.to_dict() for execution_input in execution_inputs]

    def count_by_execution(self, session: Session, execution_id: str) -> int:
        """Belirli bir execution'a ait execution input sayısını getir"""
        # 1. VALIDATION: Execution ID
        execution = self.execution_crud.find_by_id(session, execution_id)
        if not execution:
            raise BusinessLogicError(f"Execution not found: {execution_id}")
        
        # 2. OPERATION: Count execution inputs by execution
        return self.execution_input_crud.count_filtered(session, {'execution_id': execution_id})

    def count_by_workflow(self, session: Session, workflow_id: str) -> int:
        """Belirli bir workflow'a ait execution input sayısını getir"""
        # 1. VALIDATION: Workflow ID
        workflow = self.workflow_crud.find_by_id(session, workflow_id)
        if not workflow:
            raise BusinessLogicError(f"Workflow not found: {workflow_id}")
        
        # 2. OPERATION: Count execution inputs by workflow
        return self.execution_input_crud.count_filtered(session, {'workflow_id': workflow_id})

    def count_by_node(self, session: Session, node_id: str) -> int:
        """Belirli bir node'a ait execution input sayısını getir"""
        # 1. VALIDATION: Node ID
        node = self.node_crud.find_by_id(session, node_id)
        if not node:
            raise BusinessLogicError(f"Node not found: {node_id}")
        
        # 2. OPERATION: Count execution inputs by node
        return self.execution_input_crud.count_filtered(session, {'node_id': node_id})