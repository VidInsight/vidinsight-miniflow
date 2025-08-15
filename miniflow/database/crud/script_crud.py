from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from .base_crud import BaseCRUD
from ..models import Script, ScriptTestStatus
from ..decorators.auditlog_decorators import audit_create, audit_update, audit_delete, AuditMixin


class ScriptCRUD(BaseCRUD[Script], AuditMixin):

    def __init__(self):
        super().__init__(Script)
        self._init_audit()

    @audit_create("scripts")
    def create_script(self, session: Session, **script_data) -> Script:
        """Create new script with name uniqueness validation and audit logging."""
        return super().create(session, **script_data)

    @audit_update("scripts")
    def update_script(self, session: Session, script_id: str, **script_data) -> Script:
        """Update script with name uniqueness validation and audit logging."""
        return super().update(session, script_id, **script_data)

    @audit_delete("scripts")
    def delete_script(self, session: Session, script_id: str) -> Script:
        """Delete script with audit logging."""
        return super().delete(session, script_id)

    def get_by_language(self, session: Session, language: str) -> List[Script]:
        """Get all scripts by programming language."""
        return self.filter(session, {'language': language})

    def get_by_test_status(self, session: Session, test_status: ScriptTestStatus) -> List[Script]:
        """Get all scripts by test status."""
        return self.filter(session, {'test_status': test_status})