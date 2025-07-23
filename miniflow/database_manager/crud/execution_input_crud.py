from typing import List, Optional, Dict, Any
from sqlalchemy import select, and_, or_, func, desc, delete
from sqlalchemy.orm import Session, joinedload

from .base_crud import BaseCRUD
from ..models import ExecutionInput, Execution, Node, Script


class ExecutionInputCRUD(BaseCRUD[ExecutionInput]):

    def __init__(self):
        super().__init__(ExecutionInput)
    

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

    def get_execution_inputs_by_execution(self, session: Session, execution_id: str) -> List[ExecutionInput]:
        """Get all execution inputs for a specific execution"""
        stmt = select(self.model).where(self.model.execution_id == execution_id)
        return list(session.execute(stmt).scalars().all())

    # SCHEDULER SPECIFIC METHODS
    # ==============================================================
    
    def get_ready_tasks(self, session: Session, limit: int = 50) -> List[ExecutionInput]:
        """
        Get tasks ready for execution (dependency_count = 0)
        Returns tasks with joined node and script data for efficiency
        """
        stmt = (
            select(self.model)
            .options(
                joinedload(self.model.node).joinedload(Node.script),
                joinedload(self.model.execution)
            )
            .where(self.model.dependency_count == 0)
            .order_by(desc(self.model.priority), self.model.created_at)
            .limit(limit)
        )
        return list(session.execute(stmt).scalars().unique().all())

    def get_ready_tasks_with_details(self, session: Session, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get ready tasks with all necessary details for payload creation
        Returns enriched dictionaries instead of ORM objects for performance
        """
        stmt = (
            select(
                self.model.id.label('task_id'),
                self.model.execution_id,
                self.model.node_id,
                self.model.priority,
                Node.name.label('node_name'),
                Node.params.label('node_params'),
                Node.max_retries,
                Node.timeout_seconds,
                Script.id.label('script_id'),
                Script.script_path,
                Script.input_params.label('script_input_params'),
                Execution.workflow_id
            )
            .join(Node, self.model.node_id == Node.id)
            .join(Script, Node.script_id == Script.id)
            .join(Execution, self.model.execution_id == Execution.id)
            .where(self.model.dependency_count == 0)
            .order_by(desc(self.model.priority), self.model.created_at)
            .limit(limit)
        )
        
        result = session.execute(stmt).all()
        return [dict(row._mapping) for row in result]

    def bulk_delete_by_ids(self, session: Session, task_ids: List[str]) -> int:
        """
        Bulk delete execution inputs by IDs
        Returns number of deleted records
        """
        if not task_ids:
            return 0
        
        stmt = delete(self.model).where(self.model.id.in_(task_ids))
        result = session.execute(stmt)
        session.flush()
        return result.rowcount

    def decrease_dependency_count_for_nodes(self, session: Session, node_ids: List[str], 
                                          execution_id: str) -> int:
        """
        Decrease dependency count for specific nodes in an execution
        Returns number of affected records
        """
        if not node_ids:
            return 0
        
        from sqlalchemy import update
        stmt = (
            update(self.model)
            .where(
                and_(
                    self.model.execution_id == execution_id,
                    self.model.node_id.in_(node_ids),
                    self.model.dependency_count > 0
                )
            )
            .values(dependency_count=self.model.dependency_count - 1)
        )
        
        result = session.execute(stmt)
        session.flush()
        return result.rowcount

    def get_tasks_by_execution_status(self, session: Session, execution_id: str) -> List[ExecutionInput]:
        """Get all remaining tasks for a specific execution"""
        stmt = select(self.model).where(self.model.execution_id == execution_id)
        return list(session.execute(stmt).scalars().all())

    def count_ready_tasks(self, session: Session) -> int:
        """Count how many tasks are ready for execution"""
        stmt = select(func.count(self.model.id)).where(self.model.dependency_count == 0)
        return session.execute(stmt).scalar_one()

    def get_dependent_nodes(self, session: Session, completed_node_id: str, 
                           execution_id: str) -> List[str]:
        """
        Get node IDs that depend on the completed node
        Uses Edge table to find dependencies
        """
        from ..models import Edge
        stmt = (
            select(Edge.to_node_id)
            .where(
                and_(
                    Edge.from_node_id == completed_node_id,
                    Edge.workflow_id == (
                        select(Execution.workflow_id)
                        .where(Execution.id == execution_id)
                    )
                )
            )
        )
        result = session.execute(stmt).scalars().all()
        return list(result)