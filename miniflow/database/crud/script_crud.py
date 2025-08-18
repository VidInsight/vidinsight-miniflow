from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from .base_crud import BaseCRUD
from ..models import Script, ScriptTestStatus
from ..decorators.auditlog_decorators import (
    audit_create, 
    audit_update, 
    audit_delete, 
    AuditMixin
)
from ...exceptions import ValidationError


class ScriptCRUD(BaseCRUD[Script], AuditMixin):
    """
    Script entity CRUD operations.
    Manages executable script definitions with language and test status tracking.
    """

    def __init__(self):
        """Initialize ScriptCRUD with Script model and audit capabilities."""
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
        """Get all scripts filtered by programming language (Python/Bash)."""
        return self.filter(session, {'language': language})

    def get_by_test_status(self, session: Session, test_status: ScriptTestStatus) -> List[Script]:
        """Get all scripts filtered by test status (UNTESTED/PASSED/FAILED)."""
        return self.filter(session, {'test_status': test_status})