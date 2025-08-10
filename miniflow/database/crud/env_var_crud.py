from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from .base_crud import BaseCRUD
from ..models import EnvironmentVariable
from ..decorators.auditlog_decorators import audit_create, audit_update, audit_delete, AuditMixin
from ...exceptions import ValidationError, BusinessLogicError


class EnvironmentVariableCRUD(BaseCRUD[EnvironmentVariable], AuditMixin):
    """
    Environment Variable entity CRUD operations.
    Handles environment variable management with encryption support.
    """

    def __init__(self):
        super().__init__(EnvironmentVariable)

    # ============================================================================================== BUSINESS METHODS ==

    @audit_create("environment_variables")
    def create_env_var(self, session: Session, **env_var_data) -> EnvironmentVariable:
        """Create new environment variable with audit logging."""
        return super().create(session, **env_var_data)

    @audit_update("environment_variables")
    def update_env_var(self, session: Session, env_var_id: str, **env_var_data) -> EnvironmentVariable:
        """Update environment variable with audit logging."""
        return super().update(session, env_var_id, **env_var_data)

    @audit_delete("environment_variables")
    def delete_env_var(self, session: Session, env_var_id: str) -> EnvironmentVariable:
        """Delete environment variable with audit logging."""
        return super().delete(session, env_var_id)

    def get_by_name(self, session: Session, name: str) -> Optional[EnvironmentVariable]:
        """Find environment variable by name."""
        env_vars = self.filter(session, {'name': name})
        return env_vars[0] if env_vars else None

    def search_env_vars(self, session: Session, **search_criteria) -> List[EnvironmentVariable]:
        """Search environment variables based on criteria - alias for filter method."""
        return self.filter(session, search_criteria)

    def get_encrypted_vars(self, session: Session) -> List[EnvironmentVariable]:
        """Get all encrypted environment variables."""
        return self.filter(session, {'is_encrypted': True})

    def get_unencrypted_vars(self, session: Session) -> List[EnvironmentVariable]:
        """Get all unencrypted environment variables."""
        return self.filter(session, {'is_encrypted': False})

    def bulk_delete_all(self, session: Session) -> int:
        """Delete all environment variables."""
        count = self.count(session)
        if count > 0:
            # Get all IDs first
            all_vars = self.get_all(session, limit=10000)  # Large limit to get all
            all_ids = [var.id for var in all_vars]
            # Bulk delete
            return self.bulk_delete(session, all_ids)
        return 0