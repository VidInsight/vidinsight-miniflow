from sqlalchemy import select, and_, or_, func, desc, update
from sqlalchemy.exc import SQLAlchemyError
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from datetime import timezone

from .base_crud import BaseCRUD
from ..models import Execution, ExecutionStatus
from ..decorators.auditlog_decorators import (
    audit_create, 
    audit_update, 
    audit_delete, 
    AuditMixin
)
from ...exceptions import (
    ValidationError, 
    DatabaseError, 
    CRUDException
)


class ExecutionCRUD(BaseCRUD[Execution], AuditMixin):
    """
    Execution entity CRUD operations.
    Handles workflow execution lifecycle management.
    """

    def __init__(self):
        """Initialize ExecutionCRUD with Execution model and audit capabilities."""
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
        """Get execution results data for a specific execution."""
        # BaseCRUD handles validation and error handling
        execution = self.find_by_id(session, execution_id)
        if not execution:
            raise CRUDException(f"Execution not found (get_result): {execution_id}")
        return execution.results

    def get_status(self, session: Session, execution_id: str) -> ExecutionStatus:
        """Get current execution status for a specific execution."""
        # BaseCRUD handles validation and error handling
        execution = self.find_by_id(session, execution_id)
        if not execution:
            raise CRUDException(f"Execution not found (get_status): {execution_id}")
        return execution.status

    def get_by_workflow(self, session: Session, workflow_id: str) -> List[Execution]:
        """Get all executions belonging to a specific workflow."""
        return self.filter(session, {'workflow_id': workflow_id})

    def count_by_workflow(self, session: Session, workflow_id: str) -> int:
        """Count total executions for a specific workflow."""
        return self.count_filtered(session, {'workflow_id': workflow_id})

    def get_by_status(self, session: Session, status: ExecutionStatus) -> List[Execution]:
        """Get all executions filtered by execution status."""
        return self.filter(session, {'status': status})

    def count_by_status(self, session: Session, status: ExecutionStatus) -> int:
        """Count executions filtered by execution status."""
        return self.count_filtered(session, {'status': status})

    def get_by_status_and_workflow(self, session: Session, workflow_id: str, status: ExecutionStatus) -> List[Execution]:
        """Get executions filtered by both workflow and execution status."""
        return self.filter(session, {'workflow_id': workflow_id, 'status':status})

    def count_by_status_and_workflow(self, session: Session,  workflow_id: str, status: ExecutionStatus) -> int:
        """Count executions filtered by both workflow and execution status."""
        return self.count_filtered(session, {'workflow_id': workflow_id, 'status':status})

    def get_execution_statistics(self, session: Session, workflow_id: str) -> List[Execution]:
        """Get execution statistics grouped by status for a specific workflow or globally."""
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
        """Update execution status and set start timestamp."""
        # Input validation
        if not isinstance(status, ExecutionStatus):
            raise ValidationError(f"Invalid status type: {type(status).__name__}")
        
        # BaseCRUD handles database operations and error handling
        return self.update_execution(session, execution_id,
                                     status=status,
                                     started_at=datetime.now(timezone.utc))

    def set_execution_steps(self, session: Session, execution_id: str, pending_nodes: int = None, executed_nodes: int = None) -> Execution:
        """Update execution step counts for progress tracking."""
        # Input validation
        if pending_nodes is not None and (not isinstance(pending_nodes, int) or pending_nodes < 0):
            raise ValidationError("pending_nodes must be a non-negative integer")
        if executed_nodes is not None and (not isinstance(executed_nodes, int) or executed_nodes < 0):
            raise ValidationError("executed_nodes must be a non-negative integer")
        
        update_data = {}
        if pending_nodes is not None:
            update_data['pending_nodes'] = pending_nodes
        if executed_nodes is not None:
            update_data['executed_nodes'] = executed_nodes
        
        if not update_data:
            raise ValidationError("At least one step count must be provided")
            
        # BaseCRUD handles database operations and error handling
        return self.update_execution(session, execution_id, **update_data)

    def set_execution_results(self, session: Session, execution_id: str, results: Dict[str, Any]) -> Execution:
        """Set final execution results data."""
        # Input validation
        if not isinstance(results, dict):
            raise ValidationError("Results must be a dictionary")
        
        # BaseCRUD handles database operations and error handling
        return self.update_execution(session, execution_id, results=results)


    def get_executions_by_date_range(self, session: Session, start_date: datetime, end_date: datetime, 
                                   status: ExecutionStatus = None) -> List[Execution]:
        """Get executions within a date range, optionally filtered by status."""
        # Input validation
        if not isinstance(start_date, datetime) or not isinstance(end_date, datetime):
            raise ValidationError("start_date and end_date must be datetime objects")
        if start_date >= end_date:
            raise ValidationError("start_date must be before end_date")
        if status is not None and not isinstance(status, ExecutionStatus):
            raise ValidationError(f"Invalid status type: {type(status).__name__}")
        
        try:
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
        except SQLAlchemyError as e:
            raise DatabaseError(f"Failed to get executions by date range", str(e))

    def get_long_running_executions(self, session: Session, timeout_hours: int = 24) -> List[Execution]:
        """Get executions that have been running longer than the specified timeout."""
        # Input validation
        if not isinstance(timeout_hours, int) or timeout_hours <= 0:
            raise ValidationError("timeout_hours must be a positive integer")
        
        try:
            timeout_threshold = datetime.now(timezone.utc) - timedelta(hours=timeout_hours)
            stmt = select(self.model).where(
                and_(
                    self.model.status == ExecutionStatus.RUNNING,
                    self.model.started_at < timeout_threshold
                )
            ).order_by(self.model.started_at)
            return list(session.execute(stmt).scalars().all())
        except SQLAlchemyError as e:
            raise DatabaseError(f"Failed to get long running executions", str(e))