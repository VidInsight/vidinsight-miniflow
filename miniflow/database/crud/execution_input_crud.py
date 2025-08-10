from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from .base_crud import BaseCRUD
from ..models import ExecutionInput
from ..decorators.auditlog_decorators import audit_create, audit_update, audit_delete, AuditMixin


class ExecutionInputCRUD(BaseCRUD[ExecutionInput], AuditMixin):
    """
    ExecutionInput entity CRUD operations.
    Handles task queue management and ready task optimization.
    """

    def __init__(self):
        super().__init__(ExecutionInput)
        self._init_audit()

    # ==================================================================================== BUSINESS METHODS ==

    @audit_create("execution_inputs")
    def create_execution_input(self, session: Session, **kwargs) -> ExecutionInput:
        """Create new execution input with audit logging."""
        return super().create(session, **kwargs)

    @audit_update("execution_inputs")
    def update_execution_input(self, session: Session, execution_input_id: str, **kwargs) -> ExecutionInput:
        """Update execution input with audit logging."""
        return super().update(session, execution_input_id, **kwargs)

    @audit_delete("execution_inputs")
    def delete_execution_input(self, session: Session, execution_input_id: str) -> ExecutionInput:
        """Delete execution input with audit logging."""
        return super().delete(session, execution_input_id)

    def count_ready_tasks(self, session: Session) -> int:
        """Count ready tasks (dependency_count = 0)."""
        return session.query(ExecutionInput).filter(ExecutionInput.dependency_count == 0).count()

    def get_ready_tasks_with_details(self, session: Session, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get ready tasks for execution with enriched details
        Returns task data with node and workflow information
        """
        from ..models import Node, Workflow, Script
        
        # Join ExecutionInput with Node, Workflow, and Script to get detailed information
        query = session.query(
            ExecutionInput.id.label('task_id'),
            ExecutionInput.execution_id,
            ExecutionInput.node_id,
            ExecutionInput.dependency_count,
            Node.name.label('node_name'),
            Node.script_id,
            Node.params.label('node_params'),
            Node.max_retries,
            Node.timeout_seconds,
            Workflow.id.label('workflow_id'),
            Workflow.name.label('workflow_name'),
            Script.script_path.label('script_path')
        ).join(
            Node, ExecutionInput.node_id == Node.id
        ).join(
            Workflow, Node.workflow_id == Workflow.id
        ).join(
            Script, Node.script_id == Script.id
        ).filter(
            ExecutionInput.dependency_count == 0
        ).limit(limit)
        
        results = query.all()
        
        # Convert to list of dictionaries
        tasks = []
        for row in results:
            task = {
                'task_id': row.task_id,
                'execution_id': row.execution_id,
                'node_id': row.node_id,
                'node_name': row.node_name,
                'script_id': row.script_id,
                'script_path': row.script_path,
                'node_params': row.node_params,
                'max_retries': row.max_retries or 3,
                'timeout_seconds': row.timeout_seconds or 300,
                'workflow_id': row.workflow_id,
                'workflow_name': row.workflow_name,
                'dependency_count': row.dependency_count
            }
            tasks.append(task)
        
        return tasks

    def bulk_delete_by_ids(self, session: Session, task_ids: List[str]) -> int:
        """
        Bulk delete execution inputs by task IDs
        Returns number of deleted records
        """
        if not task_ids:
            return 0
            
        deleted_count = session.query(ExecutionInput).filter(
            ExecutionInput.id.in_(task_ids)
        ).delete(synchronize_session='fetch')
        
        return deleted_count

    def get_dependent_nodes(self, session: Session, completed_node_id: str, execution_id: str) -> List[str]:
        """
        Get node IDs that depend on the completed node in the given execution
        """
        from ..models import Edge
        
        # Find edges where from_node_id is the completed node
        edges_query = session.query(Edge.to_node_id).filter(
            Edge.from_node_id == completed_node_id
        )
        
        dependent_node_ids = [row.to_node_id for row in edges_query.all()]
        
        # Filter to only nodes that exist in this execution's input tasks
        if dependent_node_ids:
            existing_tasks_query = session.query(ExecutionInput.node_id).filter(
                ExecutionInput.execution_id == execution_id,
                ExecutionInput.node_id.in_(dependent_node_ids)
            )
            
            existing_dependent_nodes = [row.node_id for row in existing_tasks_query.all()]
            return existing_dependent_nodes
        
        return []

    def decrease_dependency_count_for_nodes(self, session: Session, node_ids: List[str], execution_id: str) -> int:
        """
        Decrease dependency count for multiple nodes in bulk
        Returns number of updated records
        """
        if not node_ids:
            return 0
            
        updated_count = session.query(ExecutionInput).filter(
            ExecutionInput.execution_id == execution_id,
            ExecutionInput.node_id.in_(node_ids)
        ).update(
            {ExecutionInput.dependency_count: ExecutionInput.dependency_count - 1},
            synchronize_session='fetch'
        )
        
        return updated_count

    def get_execution_inputs_by_execution(self, session: Session, execution_id: str) -> List[ExecutionInput]:
        """
        Get all execution inputs for a specific execution
        """
        return session.query(ExecutionInput).filter(
            ExecutionInput.execution_id == execution_id
        ).all()