from sqlalchemy import select, and_, or_, func, desc, update
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

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

    def get_active_executions_by_workflow(self, session, workflow_id):
        stmt = select(self.model).where(
            (self.model.workflow_id == workflow_id) & (self.model.status == 'active')
        )
        return list(session.execute(stmt).scalars().all())

    def get_executions_by_workflow(self, session: Session, workflow_id: str) -> List[Execution]:
        """Get all executions for a specific workflow."""
        return self.filter(session, {'workflow_id': workflow_id})

    def get_executions_by_status(self, session: Session, status: str) -> List[Execution]:
        """Get all executions by status."""
        return self.filter(session, {'status': status})

    def search_executions(self, session: Session, **search_criteria) -> List[Execution]:
        """Search executions based on criteria - alias for filter method."""
        return self.filter(session, search_criteria)

    def get_running_executions(self, session: Session) -> List[Execution]:
        """Get all currently running executions."""
        return self.filter(session, {'status': ExecutionStatus.RUNNING})

    def get_pending_executions(self, session: Session) -> List[Execution]:
        """Get all pending executions."""
        return self.filter(session, {'status': ExecutionStatus.PENDING})

    def get_completed_executions(self, session: Session) -> List[Execution]:
        """Get all completed executions."""
        return self.filter(session, {'status': ExecutionStatus.COMPLETED})

    def get_failed_executions(self, session: Session) -> List[Execution]:
        """Get all failed executions."""
        return self.filter(session, {'status': ExecutionStatus.FAILED})

    def get_cancelled_executions(self, session: Session) -> List[Execution]:
        """Get all cancelled executions."""
        return self.filter(session, {'status': ExecutionStatus.CANCELLED})

    def mark_execution_running(self, session: Session, execution_id: str) -> Execution:
        """Mark execution as running when first task starts"""
        execution = self.find_by_id(session, execution_id)
        
        if execution.status == ExecutionStatus.PENDING:
            execution.status = ExecutionStatus.RUNNING
            execution.updated_at = datetime.utcnow()
            session.flush()
        
        return execution

    def count_by_status(self, session: Session) -> Dict[str, int]:
        """Count executions grouped by status."""
        executions = self.get_all(session, limit=10000)  # Get all executions
        status_counts = {}
        for execution in executions:
            status = str(execution.status)
            status_counts[status] = status_counts.get(status, 0) + 1
        return status_counts

    def count_by_workflow(self, session: Session) -> Dict[str, int]:
        """Count executions grouped by workflow."""
        executions = self.get_all(session, limit=10000)  # Get all executions
        workflow_counts = {}
        for execution in executions:
            workflow_id = execution.workflow_id
            workflow_counts[workflow_id] = workflow_counts.get(workflow_id, 0) + 1
        return workflow_counts

    def get_latest_execution_for_workflow(self, session: Session, workflow_id: str) -> Optional[Execution]:
        """Get the most recent execution for a workflow."""
        executions = self.get_executions_by_workflow(session, workflow_id)
        if not executions:
            return None
        # Sort by created_at or started_at (whichever is available)
        return max(executions, key=lambda e: e.started_at or e.created_at)

    def get_execution_duration(self, session: Session, execution_id: str) -> Optional[float]:
        """Calculate execution duration in seconds."""
        execution = self.find_by_id(session, execution_id)
        if not execution.started_at:
            return None
        
        end_time = execution.ended_at or datetime.utcnow()
        duration = (end_time - execution.started_at).total_seconds()
        return duration

    def get_executions_in_date_range(self, session: Session, start_date: datetime, end_date: datetime) -> List[Execution]:
        """Get executions within a date range."""
        # This would require a more complex query with date filtering
        # For now, get all and filter in Python (not efficient for large datasets)
        executions = self.get_all(session, limit=10000)
        filtered = []
        for execution in executions:
            if execution.started_at and start_date <= execution.started_at <= end_date:
                filtered.append(execution)
        return filtered

    def update_execution_status(self, session: Session, execution_id: str, new_status: ExecutionStatus) -> Execution:
        """Update execution status with timestamp handling."""
        update_data = {'status': new_status}
        
        # Set appropriate timestamps based on status
        current_time = datetime.utcnow()
        if new_status == ExecutionStatus.RUNNING:
            update_data['started_at'] = current_time
        elif new_status in [ExecutionStatus.COMPLETED, ExecutionStatus.FAILED, ExecutionStatus.CANCELLED]:
            update_data['ended_at'] = current_time
            
        return self.update_execution(session, execution_id, **update_data)

    def set_execution_results(self, session: Session, execution_id: str, results: Dict[str, Any]) -> Execution:
        """Set execution results."""
        return self.update_execution(session, execution_id, results=results)



    def decrement_pending_nodes(self, session: Session, execution_id: str) -> Execution:
        """Decrement pending nodes count."""
        execution = self.find_by_id(session, execution_id)
        new_count = max(0, execution.pending_nodes - 1)  # Ensure non-negative
        return self.update_execution(session, execution_id, pending_nodes=new_count)

    def check_execution_completion(self, session: Session, execution_id: str) -> bool:
        """
        Check if execution is complete (all nodes finished)
        Returns True if execution should be marked as complete
        """
        execution = self.find_by_id(session, execution_id)
        if not execution:
            return False
        
        # If pending nodes is 0 or all nodes have been executed, execution is complete
        return execution.pending_nodes <= 0 or execution.executed_nodes >= execution.total_nodes

    def update_execution_progress(self, session: Session, execution_id: str, 
                                 executed_nodes: Optional[int] = None, 
                                 pending_nodes: Optional[int] = None) -> Execution:
        """
        Update execution progress counters
        Only updates provided fields, preserves others
        """
        execution = self.find_by_id(session, execution_id)
        
        if executed_nodes is not None:
            execution.executed_nodes = executed_nodes
        if pending_nodes is not None:
            execution.pending_nodes = pending_nodes
            
        execution.updated_at = datetime.utcnow()
        session.flush()
        return execution

    def increment_executed_nodes(self, session: Session, execution_id: str) -> Execution:
        """
        Increment executed nodes count and decrement pending nodes count
        Atomic operation for thread safety
        """
        stmt = (
            update(self.model)
            .where(self.model.id == execution_id)
            .values(
                executed_nodes=self.model.executed_nodes + 1,
                pending_nodes=self.model.pending_nodes - 1,
                updated_at=datetime.utcnow()
            )
        )
        
        session.execute(stmt)
        session.flush()
        
        return self.find_by_id(session, execution_id)

    def get_active_executions(self, session: Session) -> List[Execution]:
        """Get all executions with RUNNING or PENDING status"""
        stmt = (
            select(self.model)
            .where(
                self.model.status.in_([ExecutionStatus.RUNNING, ExecutionStatus.PENDING])
            )
            .order_by(desc(self.model.started_at))
        )
        return list(session.execute(stmt).scalars().all())

    def mark_execution_completed(self, session: Session, execution_id: str, 
                               final_status: ExecutionStatus = ExecutionStatus.COMPLETED,
                               results: Optional[Dict[str, Any]] = None, 
                               ended_at: Optional[datetime] = None) -> Execution:
        """
        Mark execution as completed with final results
        Updates status, results, and end time
        """
        execution = self.find_by_id(session, execution_id)
        
        execution.status = final_status
        execution.ended_at = ended_at or datetime.utcnow()
        
        if results is not None:
            # Merge with existing results if any
            current_results = execution.results or {}
            current_results.update(results)
            execution.results = current_results
        
        execution.updated_at = datetime.utcnow()
        session.flush()
        return execution

    def get_executions_by_status(self, session: Session, status: ExecutionStatus, 
                                limit: int = 100) -> List[Execution]:
        """Get executions filtered by status"""
        stmt = (
            select(self.model)
            .where(self.model.status == status)
            .order_by(desc(self.model.started_at))
            .limit(limit)
        )
        return list(session.execute(stmt).scalars().all())