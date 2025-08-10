from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from .base_crud import BaseCRUD
from ..models import Script, ScriptType, ScriptTestStatus, Node
from ..decorators.auditlog_decorators import audit_create, audit_update, audit_delete, AuditMixin
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

    def get_by_name(self, session: Session, name: str) -> Optional[Script]:
        """Find script by name."""
        scripts = self.filter(session, {'name': name})
        return scripts[0] if scripts else None

    def check_name_exists(self, session: Session, name: str) -> bool:
        """Check if script name already exists."""
        return self.get_by_name(session, name) is not None

    def search_scripts(self, session: Session, **search_criteria) -> List[Script]:
        """Search scripts based on criteria - alias for filter method."""
        return self.filter(session, search_criteria)

    def get_by_language(self, session: Session, language: str) -> List[Script]:
        """Get all scripts by programming language."""
        return self.filter(session, {'language': language})

    def get_by_test_status(self, session: Session, test_status: str) -> List[Script]:
        """Get all scripts by test status."""
        return self.filter(session, {'test_status': test_status})

    def count_by_language(self, session: Session) -> Dict[str, int]:
        """Count scripts grouped by language."""
        scripts = self.get_all(session, limit=10000)  # Get all scripts
        language_counts = {}
        for script in scripts:
            lang = script.language
            language_counts[lang] = language_counts.get(lang, 0) + 1
        return language_counts

    def count_by_test_status(self, session: Session) -> Dict[str, int]:
        """Count scripts grouped by test status."""
        scripts = self.get_all(session, limit=10000)  # Get all scripts
        status_counts = {}
        for script in scripts:
            status = script.test_status
            status_counts[status] = status_counts.get(status, 0) + 1
        return status_counts

    def get_scripts_used_by_nodes(self, session: Session) -> List[Script]:
        """Get scripts that are currently being used by nodes."""
        # This would require a join with nodes table to find referenced scripts
        # For now, we'll return empty list but the method is available for future implementation
        return []

    def get_unused_scripts(self, session: Session) -> List[Script]:
        """Get scripts that are not currently being used by any nodes."""
        # This would require a join with nodes table to find unreferenced scripts
        # For now, return all scripts but this should be implemented with proper joins
        return self.get_all(session, limit=10000)