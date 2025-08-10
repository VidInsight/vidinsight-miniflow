from typing import List, Optional, Dict, Any, Union
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, func

from .base_crud import BaseCRUD
from ..models import ExecutionOutput, ExecutionOutputStatus, Execution, Node
from ..decorators.auditlog_decorators import audit_create, audit_update, audit_delete, AuditMixin


class ExecutionOutputCRUD(BaseCRUD[ExecutionOutput], AuditMixin):
    """
    ExecutionOutput entity CRUD operations.
    Handles result collection and dynamic parameter resolution.
    """

    def __init__(self):
        super().__init__(ExecutionOutput)
        self._init_audit()

    # ==================================================================================== BUSINESS METHODS ==

    @audit_create("execution_outputs")
    def create_execution_output(self, session: Session, **kwargs) -> ExecutionOutput:
        """Create new execution output with audit logging."""
        return super().create(session, **kwargs)

    @audit_update("execution_outputs")
    def update_execution_output(self, session: Session, execution_output_id: str, **kwargs) -> ExecutionOutput:
        """Update execution output with audit logging."""
        return super().update(session, execution_output_id, **kwargs)

    @audit_delete("execution_outputs")
    def delete_execution_output(self, session: Session, execution_output_id: str) -> ExecutionOutput:
        """Delete execution output with audit logging."""
        return super().delete(session, execution_output_id)

    def check_output_exists(self, session: Session, execution_id: str, node_id: str) -> bool:
        """Check if execution output exists for given execution and node."""
        outputs = self.filter(session, {'execution_id': execution_id, 'node_id': node_id})
        return len(outputs) > 0

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