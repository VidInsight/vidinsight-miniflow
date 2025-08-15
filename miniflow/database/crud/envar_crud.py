from typing import List, Optional, Dict, Any

from sqlalchemy.orm import Session

from .base_crud import BaseCRUD
from ..models import EnvironmentVariable
from ..decorators.auditlog_decorators import audit_create, audit_update, audit_delete, AuditMixin
from ...exceptions import ValidationError, BusinessLogicError


class EnvarCRUD(BaseCRUD[EnvironmentVariable], AuditMixin):
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

    def get_by_encryption(self, session: Session, is_encrypted: bool) -> List[EnvironmentVariable]:
        """Get all encrypted environment variables."""
        return self.filter(session, {'is_encrypted': is_encrypted})