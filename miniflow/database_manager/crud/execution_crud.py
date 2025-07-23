from typing import List, Optional, Dict, Any
from sqlalchemy import select, and_, or_, func, desc, update
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from .base_crud import BaseCRUD
from ..models import Execution, ExecutionStatus


class ExecutionCRUD(BaseCRUD[Execution]):

    def __init__(self):
        super().__init__(Execution)

    
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

    def get_active_executions_by_workflow(self, session, workflow_id):
        stmt = select(self.model).where(
            (self.model.workflow_id == workflow_id) & (self.model.status == 'active')
        )
        return list(session.execute(stmt).scalars().all())

    # SCHEDULER SPECIFIC METHODS
    # ==============================================================
    
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

    def mark_execution_running(self, session: Session, execution_id: str) -> Execution:
        """Mark execution as running when first task starts"""
        execution = self.find_by_id(session, execution_id)
        
        if execution.status == ExecutionStatus.PENDING:
            execution.status = ExecutionStatus.RUNNING
            execution.updated_at = datetime.utcnow()
            session.flush()
        
        return execution

    def check_execution_completion(self, session: Session, execution_id: str) -> bool:
        """
        Check if execution is complete (pending_nodes = 0)
        Returns True if complete, False otherwise
        """
        execution = self.find_by_id(session, execution_id)
        return execution.pending_nodes <= 0

    def get_execution_statistics(self, session: Session, execution_id: str) -> Dict[str, Any]:
        """
        Get comprehensive execution statistics
        """
        execution = self.find_by_id(session, execution_id)
        
        # Calculate duration
        duration_seconds = None
        if execution.ended_at and execution.started_at:
            duration_seconds = (execution.ended_at - execution.started_at).total_seconds()
        elif execution.started_at:
            duration_seconds = (datetime.utcnow() - execution.started_at).total_seconds()
        
        return {
            'execution_id': execution.id,
            'workflow_id': execution.workflow_id,
            'status': execution.status.value,
            'pending_nodes': execution.pending_nodes,
            'executed_nodes': execution.executed_nodes,
            'total_nodes': execution.pending_nodes + execution.executed_nodes,
            'completion_percentage': (
                (execution.executed_nodes / (execution.pending_nodes + execution.executed_nodes)) * 100
                if (execution.pending_nodes + execution.executed_nodes) > 0 else 0
            ),
            'started_at': execution.started_at.isoformat() if execution.started_at else None,
            'ended_at': execution.ended_at.isoformat() if execution.ended_at else None,
            'duration_seconds': duration_seconds,
            'results': execution.results or {}
        }

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

    def get_long_running_executions(self, session: Session, 
                                   threshold_minutes: int = 60) -> List[Execution]:
        """Get executions that have been running longer than threshold"""
        threshold_time = datetime.utcnow() - timedelta(minutes=threshold_minutes)
        
        stmt = (
            select(self.model)
            .where(
                and_(
                    self.model.status == ExecutionStatus.RUNNING,
                    self.model.started_at < threshold_time
                )
            )
            .order_by(self.model.started_at)
        )
        return list(session.execute(stmt).scalars().all())