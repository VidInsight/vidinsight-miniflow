from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from .base_crud import BaseCRUD
from ..models import Script, ScriptType, ScriptTestStatus, Node
from ..decorators import audit_create, audit_update, audit_delete, AuditMixin
from ...exceptions import ValidationError, BusinessLogicError


class ScriptCRUD(BaseCRUD[Script], AuditMixin):
    """
    Script entity CRUD operations.
    Handles reusable script component management with validation.
    """

    def __init__(self):
        super().__init__(Script)
        self._init_audit()

    # ==================================================================================== BUSINESS METHODS ==

    @audit_create("scripts")
    def create_script(self, session: Session, **script_data) -> Script:
        """Create new script with name uniqueness validation and audit logging."""
        if self.check_name_exists(session, script_data['name']):
            raise ValidationError(f"Script with name '{script_data['name']}' already exists")

        return super().create(session, **script_data)

    @audit_update("scripts")
    def update_script(self, session: Session, script_id: str, **script_data) -> Script:
        """Update script with name uniqueness validation and audit logging."""
        existing_script = self.find_by_id(session, script_id)
        
        if 'name' in script_data and script_data['name'] != existing_script.name:
            if self.check_name_exists(session, script_data['name']):
                raise ValidationError(f"Script with name '{script_data['name']}' already exists")
        
        return super().update(session, script_id, **script_data)

    @audit_delete("scripts")
    def delete_script(self, session: Session, script_id: str) -> Script:
        """Delete script with audit logging."""
        return super().delete(session, script_id)
