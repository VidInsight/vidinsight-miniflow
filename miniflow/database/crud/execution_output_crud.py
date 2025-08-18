from typing import List, Optional, Dict, Any, Union
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, func

from .base_crud import BaseCRUD
from ..models import ExecutionOutput, ExecutionOutputStatus, Execution, Node
from ..decorators.auditlog_decorators import (
    audit_create, 
    audit_update, 
    audit_delete, 
    AuditMixin
)
from ...exceptions import (
    ValidationError, 
    CRUDException
)


class ExecutionOutputCRUD(BaseCRUD[ExecutionOutput], AuditMixin):
    """
    ExecutionOutput entity CRUD operations.
    Handles result collection and dynamic parameter resolution.
    """

    def __init__(self):
        """Initialize ExecutionOutputCRUD with ExecutionOutput model and audit capabilities."""
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

    def count_by_status(self, session: Session, status: ExecutionOutputStatus) -> int:
        """Count execution outputs filtered by status."""
        return self.count_filtered(session, {'status': status})

    def count_by_execution(self, session: Session, execution_id: str) -> int:
        """Count execution outputs for a specific execution."""
        return self.count_filtered(session, {'execution_id': execution_id})

    def get_by_status(self, session: Session, status: ExecutionOutputStatus) -> List[ExecutionOutput]:
        """Get execution outputs filtered by status."""
        return self.filter(session, {'status': status})

    def get_by_execution(self, session: Session, execution_id: str) -> List[ExecutionOutput]:
        """Get all execution outputs for a specific execution."""
        return self.filter(session, {'execution_id': execution_id})

    def get_result(self, session: Session, record_id: str) -> Dict[str, Any]:
        """Get result data from a specific execution output record."""
        # BaseCRUD handles validation and error handling
        record = self.find_by_id(session, record_id)
        if not record:
            raise CRUDException(f"ExecutionOutput not found (get_result): {record_id}")
        return record.result_data or {}

    def get_result_by_node_and_execution(self, session: Session, node_id: str, execution_id: str) -> Dict[str, Any]:
        """Get result data for a specific node within an execution."""
        # Input validation
        if not node_id or not node_id.strip():
            raise ValidationError("node_id cannot be empty")
        if not execution_id or not execution_id.strip():
            raise ValidationError("execution_id cannot be empty")
        
        # BaseCRUD filter handles database operations
        outputs = self.filter(session, {'node_id': node_id, 'execution_id': execution_id})
        
        if not outputs:
            return {}
        
        # İlk (ve tek olması gereken) kaydın result_data'sını döndür
        return outputs[0].result_data or {}

    def collect_all_results(self, session: Session, execution_id: str) -> Dict[str, Any]:
        """Collect and aggregate all execution results with timing information."""
        outputs = self.filter(session, {'execution_id': execution_id})
        
        results = {}
        for output in outputs:
            duration = None
            if output.started_at and output.ended_at:
                duration = (output.ended_at - output.started_at).total_seconds()
            
            results[output.node_id] = {
                'status': output.status.value,
                'started_at': output.started_at.isoformat() if output.started_at else None,
                'ended_at': output.ended_at.isoformat() if output.ended_at else None,
                'duration': duration,
                'results': output.result_data or {}
            }
        
        return results

