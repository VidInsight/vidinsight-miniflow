# orchestration/edge_orchestrator.py
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, List

from .base_orchestration import BaseOrchestration
from ...exceptions import ValidationError, BusinessLogicError


class EdgeOrchestrator(BaseOrchestration):
    """
    Edge orchestration operations for workflow connection management.
    
    Provides high-level operations for creating, updating, deleting, and managing
    workflow node connections with proper validation, cycle detection, and
    dependency management.
    """

    def __init__(self):
        """
        Initialize EdgeOrchestrator.
        
        Args:
            None
            
        Returns:
            None
            
        Raises:
            None
        """
        super().__init__()

    def create(self, session: Session, edge_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new workflow edge with comprehensive validation.
        
        Args:
            session (Session): Database session for transaction management
            edge_data (Dict[str, Any]): Edge data including from_node_id, to_node_id, condition_type
            
        Returns:
            Dict[str, Any]: Created edge data in dictionary format
            
        Raises:
            BusinessLogicError: If nodes not found or not in same workflow
            ValidationError: If edge creates cycle or already exists
            DatabaseError: If database operation fails
        """
        # 1. VALIDATION: From Node ID
        from_node_id = edge_data.get('from_node_id')
        from_node = self.node_crud.find_by_id(session, from_node_id)
        if not from_node:
            raise BusinessLogicError(f"From node not found: {from_node_id}")
        
        # 2. VALIDATION: To Node ID
        to_node_id = edge_data.get('to_node_id')
        to_node = self.node_crud.find_by_id(session, to_node_id)
        if not to_node:
            raise BusinessLogicError(f"To node not found: {to_node_id}")
        
        # 3. VALIDATION: Check if nodes are in the same workflow
        if from_node.workflow_id != to_node.workflow_id:
            raise ValidationError("Nodes must be in the same workflow")
        
        # 4. VALIDATION: Check for self-loop
        if from_node_id == to_node_id:
            raise ValidationError("Self-loops are not allowed")
            
        # 5. VALIDATION: Check if edge already exists
        if self.edge_crud.check_edge_exists(session, from_node.workflow_id, from_node_id, to_node_id):
            raise ValidationError(f"Edge already exists between nodes {from_node.name} and {to_node.name}")
        
        # 6. OPERATION: Ensure workflow_id consistency
        edge_data['workflow_id'] = from_node.workflow_id
        
        # 7. OPERATION: Create Edge
        edge = self.edge_crud.create_edge(session, **edge_data)

        # 8. RETURN: API Format
        return edge.to_dict()

    def update(self, session: Session, edge_id: str, edge_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update existing edge with validation.
        
        Args:
            session (Session): Database session for transaction management
            edge_id (str): Unique identifier of edge to update
            edge_data (Dict[str, Any]): Updated edge data
            
        Returns:
            Dict[str, Any]: Updated edge data in dictionary format
            
        Raises:
            BusinessLogicError: If edge or nodes not found
            ValidationError: If update creates invalid connection
            DatabaseError: If database operation fails
        """
        # 1. VALIDATION: Edge ID
        old_edge = self.edge_crud.find_by_id(session, edge_id)
        if not old_edge:
            raise BusinessLogicError(f"Edge not found: {edge_id}")

        # 2. VALIDATION: Check if nodes are in the same workflow
        if 'from_node_id' in edge_data or 'to_node_id' in edge_data:
            from_node_id = edge_data.get('from_node_id', old_edge.from_node_id)
            to_node_id = edge_data.get('to_node_id', old_edge.to_node_id)

            # Validate nodes exist
            from_node = self.node_crud.find_by_id(session, from_node_id)
            if not from_node:
                raise BusinessLogicError(f"From node not found: {from_node_id}")
            
            to_node = self.node_crud.find_by_id(session, to_node_id)
            if not to_node:
                raise BusinessLogicError(f"To node not found: {to_node_id}")

            # Check same workflow
            if from_node.workflow_id != to_node.workflow_id:
                raise ValidationError("Nodes must be in the same workflow")

            # Check for circular dependency
            if from_node_id == to_node_id:
                raise ValidationError("Self-loops are not allowed")

            # Check if edge already exists (unless updating to the same edge)
            if (from_node_id != old_edge.from_node_id or to_node_id != old_edge.to_node_id):
                if self.edge_crud.check_edge_exists(session, from_node.workflow_id, from_node_id, to_node_id):
                    raise ValidationError(f"Edge already exists between nodes {from_node.name} and {to_node.name}")

        # 3. OPERATION: Update Edge
        updated_edge = self.edge_crud.update_edge(session, edge_id, **edge_data)

        # 4. RETURN: API Format
        return updated_edge.to_dict()

    def delete(self, session: Session, edge_id: str) -> Dict[str, Any]:
        """
        Delete edge by ID with validation.
        
        Args:
            session (Session): Database session for transaction management
            edge_id (str): Unique identifier of edge to delete
            
        Returns:
            Dict[str, Any]: Deleted edge data in dictionary format
            
        Raises:
            BusinessLogicError: If edge with given ID not found
            DatabaseError: If database operation fails
        """
        # 1. VALIDATION: Edge ID
        edge = self.edge_crud.find_by_id(session, edge_id)
        if not edge:
            raise BusinessLogicError(f"Edge not found: {edge_id}")

        # 2. OPERATION: Delete Edge
        deleted_edge = self.edge_crud.delete_edge(session, edge_id)

        # 3. RETURN: API Format
        return deleted_edge.to_dict()

    def validate(self, session: Session, edge_id: str) -> Dict[str, Any]:
        """Edge doğrulama"""
        # 1. VALIDATION: Edge ID
        edge = self.edge_crud.find_by_id(session, edge_id)
        if not edge:
            raise BusinessLogicError(f"Edge not found: {edge_id}")

        validation_errors = []
        validation_warnings = []

        # 2. VALIDATION: From Node ID
        from_node = self.node_crud.find_by_id(session, edge.from_node_id)
        if not from_node:
            validation_errors.append(f"From node not found: {edge.from_node_id}")

        # 3. VALIDATION: To Node ID
        to_node = self.node_crud.find_by_id(session, edge.to_node_id)
        if not to_node:
            validation_errors.append(f"To node not found: {edge.to_node_id}")

        # 4. VALIDATION: Check if nodes are in the same workflow (only if both nodes exist)
        if from_node and to_node and from_node.workflow_id != to_node.workflow_id:
            validation_errors.append("Nodes must be in the same workflow")

        # 5. VALIDATION: Check for circular dependency
        if edge.from_node_id == edge.to_node_id:
            validation_errors.append("Self-loops are not allowed")

        # 6. VALIDATION: Return validation result
        is_valid = len(validation_errors) == 0
        return {
            'edge_id': edge_id,
            'is_valid': is_valid,
            'validation_errors': validation_errors,
            'validation_warnings': validation_warnings
        }

    def search(self, session: Session, search_criteria: Dict[str, Any], skip: int = 0, limit: int = 100, order_by_field: str = None) -> Dict[str, Any]:
        """Edge arama"""
        # 1. OPERATION: Search edges
        edges = self.edge_crud.filter(session, search_criteria, skip=skip, limit=limit, order_by_field=order_by_field)

        # Get total count for pagination
        total_count = self.edge_crud.count_filtered(session, search_criteria)

        # 2. RETURN: API Format
        return {
            'data': [edge.to_dict() for edge in edges],
            'total_count': total_count,
            'skip': skip,
            'limit': limit,
            'has_more': (skip + limit) < total_count
        }
        
    def get_all(self, session: Session) -> List[Dict[str, Any]]:
        """Tüm edge'leri getir"""
        edges = self.edge_crud.get_all(session)
        return [edge.to_dict() for edge in edges]

    def get_by_workflow(self, session: Session, workflow_id: str) -> List[Dict[str, Any]]:
        """Belirli bir workflow'a ait edge'leri getir"""
        # 1. VALIDATION: Workflow ID
        workflow = self.workflow_crud.find_by_id(session, workflow_id)
        if not workflow:
            raise BusinessLogicError(f"Workflow not found: {workflow_id}")
        
        # 2. OPERATION: Get edges by workflow
        edges = self.edge_crud.get_by_workflow(session, workflow_id)
        return [edge.to_dict() for edge in edges]

    def get(self, session: Session, edge_id: str, include_details: bool = False) -> Dict[str, Any]:
        """Edge detayını getir"""
        # 1. VALIDATION: Edge ID
        edge = self.edge_crud.find_by_id(session, edge_id)
        if not edge:
            raise BusinessLogicError(f"Edge not found: {edge_id}")

        # 2. OPERATION: Get base edge data
        edge_dict = edge.to_dict()

        # 3. OPERATION: Add enhanced details if requested
        if include_details:
            # Add node names and details
            from_node = self.node_crud.find_by_id(session, edge.from_node_id)
            to_node = self.node_crud.find_by_id(session, edge.to_node_id)
            
            edge_dict['from_node_name'] = from_node.name if from_node else None
            edge_dict['to_node_name'] = to_node.name if to_node else None
            
            # Add workflow name
            workflow = self.workflow_crud.find_by_id(session, edge.workflow_id)
            edge_dict['workflow_name'] = workflow.name if workflow else None

        # 4. RETURN: API Format
        return edge_dict

    def count(self, session: Session) -> int:
        """Edge sayısını getir"""
        return self.edge_crud.count(session)
    
    def exists(self, session: Session, edge_id: str) -> bool:
        """Edge var mı kontrolü"""
        return self.edge_crud.exists(session, edge_id)
