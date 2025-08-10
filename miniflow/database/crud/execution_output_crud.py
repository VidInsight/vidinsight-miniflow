from typing import List, Optional, Dict, Any, Union
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.orm import Session
from datetime import datetime

from .base_crud import BaseCRUD
from ..models import ExecutionOutput, ExecutionOutputStatus, Execution, Node


class ExecutionOutputCRUD(BaseCRUD[ExecutionOutput]):
    
    def __init__(self):
        super().__init__(ExecutionOutput)

    
    """
    BaseCRUD'dan miras alınan fonksiyonlar:
    ============================================================
    - create()
    - find_by_id()
    - find_by_name() 
    - update()
    - delete()
    - get_all()
    - count(), 
    - exists()
    - filter() 
    - order_by()
    - select_in_bulk()
    - truncate(),
    - bulk_create()
    - bulk_update()
    - bulk_delete()
    """

    def get_execution_outputs_by_execution(self, session: Session, execution_id: str) -> List[ExecutionOutput]:
        """Get all execution outputs for a specific execution"""
        stmt = select(self.model).where(self.model.execution_id == execution_id)
        return list(session.execute(stmt).scalars().all())

    # SCHEDULER SPECIFIC METHODS
    # ==============================================================
    
    def create_execution_output(self, session: Session, execution_id: str, node_id: str, 
                               status: ExecutionOutputStatus, result_data: Optional[Dict[str, Any]] = None,
                               started_at: Optional[datetime] = None, 
                               ended_at: Optional[datetime] = None) -> ExecutionOutput:
        """
        Create execution output with all required fields
        Uses proper enum types and handles datetime defaults
        """
        output_data = {
            'execution_id': execution_id,
            'node_id': node_id,
            'status': status,
            'result_data': result_data or {},
            'started_at': started_at or datetime.utcnow(),
            'ended_at': ended_at or datetime.utcnow()
        }
        
        return self.create(session, **output_data)

    def get_outputs_by_execution_and_status(self, session: Session, execution_id: str, 
                                           status: ExecutionOutputStatus) -> List[ExecutionOutput]:
        """Get execution outputs filtered by execution and status"""
        stmt = (
            select(self.model)
            .where(
                and_(
                    self.model.execution_id == execution_id,
                    self.model.status == status
                )
            )
        )
        return list(session.execute(stmt).scalars().all())

    def get_completed_nodes_for_execution(self, session: Session, execution_id: str) -> List[str]:
        """Get list of completed node IDs for an execution"""
        stmt = (
            select(self.model.node_id)
            .where(
                and_(
                    self.model.execution_id == execution_id,
                    self.model.status == ExecutionOutputStatus.SUCCESS
                )
            )
        )
        result = session.execute(stmt).scalars().all()
        return list(result)

    def get_execution_results_for_dependency_resolution(self, session: Session, 
                                                       execution_id: str, 
                                                       node_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Get execution results for specific nodes to resolve dynamic dependencies
        Returns: {node_id: {node_name: result_data}}
        """
        if not node_ids:
            return {}
        
        stmt = (
            select(
                self.model.node_id,
                self.model.result_data,
                Node.name.label('node_name')
            )
            .join(Node, self.model.node_id == Node.id)
            .where(
                and_(
                    self.model.execution_id == execution_id,
                    self.model.node_id.in_(node_ids),
                    self.model.status == ExecutionOutputStatus.SUCCESS
                )
            )
        )
        
        results = session.execute(stmt).all()
        
        # Build the dependency resolution dictionary
        dependency_data = {}
        for row in results:
            dependency_data[row.node_id] = {
                'node_name': row.node_name,
                'result_data': row.result_data or {}
            }
        
        return dependency_data

    def check_output_exists(self, session: Session, execution_id: str, node_id: str) -> bool:
        """Check if execution output already exists for a node"""
        stmt = (
            select(func.count(self.model.id))
            .where(
                and_(
                    self.model.execution_id == execution_id,
                    self.model.node_id == node_id
                )
            )
        )
        count = session.execute(stmt).scalar_one()
        return count > 0

    def get_execution_progress(self, session: Session, execution_id: str) -> Dict[str, int]:
        """
        Get execution progress statistics
        Returns counts by status
        """
        stmt = (
            select(
                self.model.status,
                func.count(self.model.id).label('count')
            )
            .where(self.model.execution_id == execution_id)
            .group_by(self.model.status)
        )
        
        results = session.execute(stmt).all()
        
        progress = {
            'success': 0,
            'failure': 0,
            'timeout': 0,
            'cancelled': 0,
            'total': 0
        }
        
        for row in results:
            status_key = row.status.value.lower()  # Convert enum to string
            progress[status_key] = row.count
            progress['total'] += row.count
            
        return progress

    def get_node_result_data(self, session: Session, execution_id: str, 
                            node_name: str) -> Optional[Dict[str, Any]]:
        """
        Get result data for a specific node by name
        Used for dynamic parameter resolution
        """
        stmt = (
            select(self.model.result_data)
            .join(Node, self.model.node_id == Node.id)
            .where(
                and_(
                    self.model.execution_id == execution_id,
                    Node.name == node_name,
                    self.model.status == ExecutionOutputStatus.SUCCESS
                )
            )
        )
        
        result = session.execute(stmt).scalar_one_or_none()
        return result or {}