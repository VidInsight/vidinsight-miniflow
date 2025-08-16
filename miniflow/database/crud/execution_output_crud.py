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

    def count_by_status(self, session: Session, status: ExecutionOutputStatus) -> int:
        """Status'a göre sayım."""
        return self.count_filtered(session, {'status': status})

    def count_by_execution(self, session: Session, execution_id: str) -> int:
        """Execution'a göre sayım."""
        return self.count_filtered(session, {'execution_id': execution_id})

    def get_by_status(self, session: Session, status: ExecutionOutputStatus) -> List[ExecutionOutput]:
        """Status'a göre kayıtlar."""
        return self.filter(session, {'status': status})

    def get_by_execution(self, session: Session, execution_id: str) -> List[ExecutionOutput]:
        """Execution'a göre kayıtlar."""
        return self.filter(session, {'execution_id': execution_id})

    def get_result(self, session: Session, record_id: str) -> List[Dict[str, Any]]:
        """Seçilen kayıtların result_data kolonunu JSON olarak döndür."""
        record = self.find_by_id(session, record_id)
        return record.result_data or {}

    def get_result_by_node_and_execution(self, session: Session, node_id: str, execution_id: str) -> Dict[str, Any]:
        """Node'a ve execution'a göre result_data kolonunu JSON olarak döndür."""
        # Belirli node_id ve execution_id ile kayıt bul
        outputs = self.filter(session, {'node_id': node_id, 'execution_id': execution_id})
        
        if not outputs:
            return {}
        
        # İlk (ve tek olması gereken) kaydın result_data'sını döndür
        return outputs[0].result_data or {}

    def collect_all_results(self, session: Session, execution_id: str) -> Dict[str, Any]:
        """Execution'a ait tüm sonuçları topla ve basit JSON formatla döndür."""
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

