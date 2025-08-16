from sqlalchemy import select, and_, or_, func, desc, update
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from datetime import timezone

from .base_crud import BaseCRUD
from ..models import Execution, ExecutionStatus
from ..decorators.auditlog_decorators import audit_create, audit_update, audit_delete, AuditMixin


class ExecutionCRUD(BaseCRUD[Execution], AuditMixin):
    """
    Execution entity CRUD operations.
    Handles workflow execution lifecycle management.
    """

    def __init__(self):
        super().__init__(Execution)
        self._init_audit()

    # ============================================================================================== BUSINESS METHODS ==

    @audit_create("executions")
    def create_execution(self, session: Session, **kwargs) -> Execution:
        """Create new execution with audit logging."""
        return super().create(session, **kwargs)

    @audit_update("executions")
    def update_execution(self, session: Session, execution_id: str, **kwargs) -> Execution:
        """Update execution with audit logging."""
        return super().update(session, execution_id, **kwargs)

    @audit_delete("executions")
    def delete_execution(self, session: Session, execution_id: str) -> Execution:
        """Delete execution with audit logging."""
        return super().delete(session, execution_id)

    # ============================================================================================== BUSINESS METHODS ==
    def get_result(self, session: Session, execution_id: str):
        execution = self.find_by_id(session, execution_id)
        return execution.results

    def get_status(self, session: Session, execution_id: str) -> ExecutionStatus:
        execution = self.find_by_id(session, execution_id)
        return execution.status

    def get_by_workflow(self, session: Session, workflow_id: str) -> List[Execution]:
        return self.filter(session, {'workflow_id': workflow_id})

    def count_by_workflow(self, session: Session, workflow_id: str) -> int:
        return self.count_filtered(session, {'workflow_id': workflow_id})

    def get_by_status(self, session: Session, status: ExecutionStatus) -> List[Execution]:
        """Get all executions with given status."""
        return self.filter(session, {'status': status})

    def count_by_status(self, session: Session, status: ExecutionStatus) -> List[Execution]:
        return self.count_filtered(session, {'status': status})

    def get_by_status_and_workflow(self, session: Session, workflow_id: str, status: ExecutionStatus) -> List[Execution]:
        return self.filter(session, {'workflow_id': workflow_id, 'status':status})

    def count_by_status_and_workflow(self, session: Session,  workflow_id: str, status: ExecutionStatus) -> List[Execution]:
        return self.count_filtered(session, {'workflow_id': workflow_id, 'status':status})

    def get_execution_statistics(self, session: Session, workflow_id: str) -> List[Execution]:
        filters = {}
        if workflow_id:
            filters['workflow_id'] = workflow_id

        stats = {}
        for status in ExecutionStatus:
            if workflow_id:
                count = self.count_filtered(session, {**filters, 'status': status})
            else:
                count = self.count_filtered(session, {'status': status})
            stats[status.value] = count

        return stats

    def set_execution_status(self, session: Session, execution_id: str, status: ExecutionStatus) -> Execution:
        return self.update_execution(session, execution_id,
                                     status=status,
                                     started_at=datetime.now(timezone.utc))

    def set_execution_steps(self, session: Session, execution_id: str, pending_nodes: int = None, executed_nodes: int = None) -> Execution:
        """Update execution step counts (pending_nodes and executed_nodes)."""
        update_data = {}
        if pending_nodes is not None:
            update_data['pending_nodes'] = pending_nodes
        if executed_nodes is not None:
            update_data['executed_nodes'] = executed_nodes
        
        if not update_data:
            raise ValueError("At least one step count must be provided")
            
        return self.update_execution(session, execution_id, **update_data)

    def set_execution_results(self, session: Session, execution_id: str, results: Dict[str, Any]) -> Execution:
        """Set execution results."""
        return self.update_execution(session, execution_id, results=results)


    def get_executions_by_date_range(self, session: Session, start_date: datetime, end_date: datetime, 
                                   status: ExecutionStatus = None) -> List[Execution]:
        """Get executions within a date range, optionally filtered by status."""
        stmt = select(self.model).where(
            and_(
                self.model.created_at >= start_date,
                self.model.created_at <= end_date
            )
        )
        
        if status:
            stmt = stmt.where(self.model.status == status)
            
        stmt = stmt.order_by(desc(self.model.created_at))
        return list(session.execute(stmt).scalars().all())

    def get_long_running_executions(self, session: Session, timeout_hours: int = 24) -> List[Execution]:
        """Get executions that have been running longer than the specified timeout."""
        timeout_threshold = datetime.now(timezone.utc) - timedelta(hours=timeout_hours)
        stmt = select(self.model).where(
            and_(
                self.model.status == ExecutionStatus.RUNNING,
                self.model.started_at < timeout_threshold
            )
        ).order_by(self.model.started_at)
        return list(session.execute(stmt).scalars().all())