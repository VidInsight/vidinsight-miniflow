# orchestration/execution_output_orchestration.py
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, Union, List
from datetime import datetime, timezone

from .base_orchestration import BaseOrchestration
from ...exceptions import ValidationError, BusinessLogicError


class ExecutionOutputOrchestrator(BaseOrchestration):
    """
    Execution output orchestration operations for result management.
    
    Provides high-level operations for managing execution outputs, result collection,
    and status tracking for workflow node executions.
    """

    def __init__(self):
        """
        Initialize ExecutionOutputOrchestrator.
        
        Args:
            None
            
        Returns:
            None
            
        Raises:
            None
        """
        super().__init__()
  
    def get_all(self, session: Session) -> List[Dict[str, Any]]:
        """
        Get all execution outputs from database.
        
        Args:
            session (Session): Database session for transaction management
            
        Returns:
            List[Dict[str, Any]]: List of all execution outputs in dictionary format
            
        Raises:
            DatabaseError: If database operation fails
        """
        execution_outputs = self.execution_output_crud.get_all(session)
        return [execution_output.to_dict() for execution_output in execution_outputs]
        
    def search(self, session: Session, search_criteria: Dict[str, Any], skip: int = 0, limit: int = 100, order_by_field: str = None) -> Dict[str, Any]:
        """
        Search execution outputs with filtering and pagination.
        
        Args:
            session (Session): Database session for transaction management
            search_criteria (Dict[str, Any]): Filter criteria for execution output search
            skip (int): Number of records to skip for pagination (default: 0)
            limit (int): Maximum number of records to return (default: 100)
            order_by_field (str, optional): Field name to order results by
            
        Returns:
            Dict[str, Any]: Search results with data, pagination info, and metadata
            
        Raises:
            ValidationError: If search criteria contains invalid fields
            DatabaseError: If database operation fails
        """
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
        """
        Get execution output by ID with validation.
        
        Args:
            session (Session): Database session for transaction management
            execution_output_id (str): Unique identifier of execution output to retrieve
            
        Returns:
            Dict[str, Any]: Execution output data in dictionary format
            
        Raises:
            BusinessLogicError: If execution output with given ID not found
            DatabaseError: If database operation fails
        """
        # 1. VALIDATION: Execution Output ID
        execution_output = self.execution_output_crud.find_by_id(session, execution_output_id)
        if not execution_output:
            raise BusinessLogicError(f"Execution output not found: {execution_output_id}")

        # 2. RETURN: API Format
        return execution_output.to_dict()

    def count(self, session: Session) -> int:
        """
        Count total number of execution outputs.
        
        Args:
            session (Session): Database session for transaction management
            
        Returns:
            int: Total count of execution outputs in database
            
        Raises:
            DatabaseError: If database operation fails
        """
        return self.execution_output_crud.count(session)
    
    def exists(self, session: Session, execution_output_id: str) -> bool:
        """
        Check if execution output exists by ID.
        
        Args:
            session (Session): Database session for transaction management
            execution_output_id (str): Unique identifier of execution output to check
            
        Returns:
            bool: True if execution output exists, False otherwise
            
        Raises:
            DatabaseError: If database operation fails
        """
        return self.execution_output_crud.exists(session, execution_output_id)

    def get_by_execution(self, session: Session, execution_id: str) -> List[Dict[str, Any]]:
        """
        Get all execution outputs for a specific execution.
        
        Args:
            session (Session): Database session for transaction management
            execution_id (str): Unique identifier of execution to get outputs for
            
        Returns:
            List[Dict[str, Any]]: List of execution outputs for the execution
            
        Raises:
            DatabaseError: If database operation fails
        """
        # 1. OPERATION: Get execution outputs by execution
        execution_outputs = self.execution_output_crud.get_by_execution(session, execution_id)
        return [execution_output.to_dict() for execution_output in execution_outputs]

    def get_by_node(self, session: Session, node_id: str) -> List[Dict[str, Any]]:
        """
        Get all execution outputs for a specific node.
        
        Args:
            session (Session): Database session for transaction management
            node_id (str): Unique identifier of node to get outputs for
            
        Returns:
            List[Dict[str, Any]]: List of execution outputs for the node
            
        Raises:
            DatabaseError: If database operation fails
        """
        # 1. OPERATION: Get execution outputs by node
        execution_outputs = self.execution_output_crud.filter(session, {'node_id': node_id})
        return [execution_output.to_dict() for execution_output in execution_outputs]

    def get_by_status(self, session: Session, status: str) -> List[Dict[str, Any]]:
        """
        Get all execution outputs with a specific status.
        
        Args:
            session (Session): Database session for transaction management
            status (str): Status to filter execution outputs by
            
        Returns:
            List[Dict[str, Any]]: List of execution outputs with the specified status
            
        Raises:
            ValidationError: If status is empty or None
            DatabaseError: If database operation fails
        """
        # 1. VALIDATION: Status
        if not status:
            raise ValidationError("Status is required")
            
        # 2. OPERATION: Get execution outputs by status
        execution_outputs = self.execution_output_crud.filter(session, {'status': status})
        return [execution_output.to_dict() for execution_output in execution_outputs]