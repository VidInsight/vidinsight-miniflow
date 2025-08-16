# orchestration/workflow_orchestrator.py
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, Union, List

from ..models import WorkflowStatus
from .base_orchestration import BaseOrchestration
from ...exceptions import ValidationError, BusinessLogicError


class WorkflowOrchestrator(BaseOrchestration):
    """ Workflow Orchestration Operations """

    def __init__(self):
        super().__init__()

    def create(self, session: Session, workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        """ Create a Workflow """

        # Validate if the name is not already in use
        existing_workflow = self.workflow_crud.find_by_name(session, workflow_data['name'])
        if existing_workflow:
            raise ValidationError(f"Workflow with name '{workflow_data['name']}' already exists")

        # Create a workflow with given params
        workflow = self.workflow_crud.create_workflow(session, **workflow_data)

        # Return
        return workflow.to_dict()

    def update(self, session: Session, workflow_id: str, workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        """ Update Workflow """

        # Validate target workflow via ID
        workflow = self.workflow_crud.find_by_id(session, workflow_id)
        if not workflow:
            raise BusinessLogicError(f"Workflow not found: {workflow_id}")

        # Validate if the name is not already in use
        if 'name' in workflow_data and workflow_data['name'] != workflow.name:
            existing_workflow = self.workflow_crud.find_by_name(session, workflow_data['name'])
            if existing_workflow and existing_workflow.id != workflow_id:
                raise ValidationError(f"Workflow with name '{workflow_data['name']}' already exists")

        # Update workflow with given params
        updated_workflow = self.workflow_crud.update_workflow(session, workflow_id, **workflow_data)

        # 4. Return
        return updated_workflow.to_dict()

    def delete(self, session: Session, workflow_id: str) -> Dict[str, Any]:
        """ Delete Workflow """

        # Validate target workflow via ID
        workflow = self.workflow_crud.find_by_id(session, workflow_id)
        if not workflow:
            raise BusinessLogicError(f"Workflow not found: {workflow_id}")

        # Delete workflow
        deleted_workflow = self.workflow_crud.delete_workflow(session, workflow_id)

        # Return
        return deleted_workflow.to_dict()

    def search(self, session: Session, search_criteria: Dict[str, Any], skip: int = 0, limit: int = 100, order_by_field: str = None) -> Dict[str, Any]:
        """ Search Workflow """

        # Search workflows with given criteria
        workflows = self.workflow_crud.filter(session, search_criteria, skip=skip, limit=limit, order_by_field=order_by_field)

        # Get total count for pagination
        total_count = self.workflow_crud.count_filtered(session, search_criteria)

        # Return
        return {
            'data': [workflow.to_dict() for workflow in workflows],
            'total_count': total_count,
            'skip': skip,
            'limit': limit,
            'has_more': (skip + limit) < total_count
        }

    def get(self, session: Session, workflow_id: str, include_details: bool) -> Dict[str, Any]:
        """ Get Workflow """

        # Validate target workflow via ID
        workflow = self.workflow_crud.find_by_id(session, workflow_id)
        if not workflow:
            raise BusinessLogicError(f"Workflow not found: {workflow_id}")

        workflow_dict = workflow.to_dict()
        
        # Get Nodes & Edges via workflow ID
        nodes = self.node_crud.get_by_workflow(session, workflow_id)
        edges = self.edge_crud.get_by_workflow(session, workflow_id)
        
        workflow_dict['node_count'] = len(nodes)
        workflow_dict['edge_count'] = len(edges)

        # Add workflow details
        if include_details:
            workflow_dict['nodes'] = [node.to_dict() for node in nodes]
            workflow_dict['edges'] = [edge.to_dict() for edge in edges]
        
        # Return
        return workflow_dict

    def get_all(self, session: Session) -> List[Dict[str, Any]]:
        """Tüm workflow'ları getir"""
        workflows = self.workflow_crud.get_all(session)
        return [workflow.to_dict() for workflow in workflows]

    def count(self, session: Session) -> int:
        """ Count Workflow """
        return self.workflow_crud.count(session)
    
    def exists(self, session: Session, workflow_id: str) -> bool:
        """ Exists Workflow """
        return self.workflow_crud.exists(session, workflow_id)

    def set_status_active(self, session: Session, workflow_id: str) -> Dict[str, Any]:
        """ Set workflow status as ACTIVE """
        # Validate target workflow via ID
        workflow = self.workflow_crud.find_by_id(session, workflow_id)
        if not workflow:
            raise BusinessLogicError(f"Workflow not found: {workflow_id}")
        
        updated_workflow = self.workflow_crud.set_status(session, workflow_id, WorkflowStatus.ACTIVE)
        return updated_workflow.to_dict()

    def set_status_draft(self, session: Session, workflow_id: str) -> Dict[str, Any]:
        """ Set workflow status as DRAFT """
        # Validate target workflow via ID
        workflow = self.workflow_crud.find_by_id(session, workflow_id)
        if not workflow:
            raise BusinessLogicError(f"Workflow not found: {workflow_id}")
        
        updated_workflow = self.workflow_crud.set_status(session, workflow_id, WorkflowStatus.DRAFT)
        return updated_workflow.to_dict()

    def get_active_workflows(self, session: Session) -> List[Dict[str, Any]]:
        """ Get workflows by status """
        workflows = self.workflow_crud.filter(session, {"status": WorkflowStatus.ACTIVE})
        return [workflow.to_dict() for workflow in workflows]

    def get_draft_workflows(self, session: Session) -> List[Dict[str, Any]]:
        """ Get workflows by status """
        workflows = self.workflow_crud.filter(session, {"status": WorkflowStatus.DRAFT})
        return [workflow.to_dict() for workflow in workflows]

    def set_priority(self, session: Session, workflow_id: str, priority: int) -> Dict[str, Any]:
        """ Set workflow priority """
        # Validate priority range
        if not isinstance(priority, int) or not 0 <= priority <= 10:
            raise ValidationError(f"Priority must be an integer between 0 and 10, got: {priority}")
        
        # Validate target workflow via ID
        workflow = self.workflow_crud.find_by_id(session, workflow_id)
        if not workflow:
            raise BusinessLogicError(f"Workflow not found: {workflow_id}")
        
        updated_workflow = self.workflow_crud.set_priority(session, workflow_id, priority)
        return updated_workflow.to_dict()

    def get_all_workflows(self, session: Session) -> List[Dict[str, Any]]:
        """ Get all workflows """
        workflows = self.workflow_crud.get_all(session)
        return [workflow.to_dict() for workflow in workflows]