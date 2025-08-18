# orchestration/envar_orchestration.py
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, Union, List

from .base_orchestration import BaseOrchestration
from ...exceptions import ValidationError, BusinessLogicError


class EnvarOrchestrator(BaseOrchestration):
    """
    Environment variable orchestration operations for configuration management.
    
    Provides high-level operations for creating, updating, deleting, and managing
    environment variables with validation, encryption support, and secure handling.
    """

    def __init__(self):
        """
        Initialize EnvarOrchestrator.
        
        Args:
            None
            
        Returns:
            None
            
        Raises:
            None
        """
        super().__init__()

    def create(self, session: Session, envar_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new environment variable with validation and encryption support.
        
        Args:
            session (Session): Database session for transaction management
            envar_data (Dict[str, Any]): Environment variable data including name, value, encryption flag
            
        Returns:
            Dict[str, Any]: Created environment variable data in dictionary format
            
        Raises:
            ValidationError: If name is invalid, empty, or already exists
            DatabaseError: If database operation fails
        """
        # 1. VALIDATION: Environment Variable Name
        name = envar_data.get('name', '').strip()
        if not name:
            raise ValidationError("Environment variable name is required")
        
        # Check if name contains only valid characters (alphanumeric, underscores, hyphens)
        if not name.replace('_', '').replace('-', '').isalnum():
            raise ValidationError("Environment variable name must contain only alphanumeric characters, hyphens, and underscores")

        # 2. VALIDATION: Check if environment variable name already exists
        existing_env_var = self.envar_crud.find_by_name(session, name)
        if existing_env_var:
            raise ValidationError(f"Environment variable with name '{name}' already exists")

        # 3. OPERATION: Handle encryption and create environment variable
        create_data = envar_data.copy()
        if create_data.get('is_encrypted', False):
            create_data['value'] = self._encrypt_value(create_data['value'])
        
        env_var = self.envar_crud.create_env_var(session, **create_data)

        # 4. RETURN: API Format
        return env_var.to_dict()
  
    def update(self, session: Session, envar_id: str, envar_data: Dict[str, Any]) -> Dict[str, Any]:
        """Environment Variable güncelleme"""
        # 1. VALIDATION: Environment Variable ID
        old_env_var = self.envar_crud.find_by_id(session, envar_id)
        if not old_env_var:
            raise BusinessLogicError(f"Environment variable not found: {envar_id}")

        # 2. VALIDATION: Environment Variable Name Uniqueness
        if 'name' in envar_data and envar_data['name'] != old_env_var.name:
            name = envar_data['name'].strip()
            if not name:
                raise ValidationError("Environment variable name is required")
            
            # Check if name contains only valid characters
            if not name.replace('_', '').replace('-', '').isalnum():
                raise ValidationError("Environment variable name must contain only alphanumeric characters, hyphens, and underscores")
            
            existing_env_var = self.envar_crud.find_by_name(session, name)
            if existing_env_var and existing_env_var.id != envar_id:
                raise ValidationError(f"Environment variable with name '{name}' already exists")
            
            # Update the name in envar_data
            envar_data['name'] = name

        # 3. OPERATION: Handle encryption and update environment variable
        update_data = envar_data.copy()
        if 'value' in update_data and update_data.get('is_encrypted', old_env_var.is_encrypted):
            update_data['value'] = self._encrypt_value(update_data['value'])
        
        updated_env_var = self.envar_crud.update_env_var(session, envar_id, **update_data)
        
        # 4. RETURN: API Format
        return updated_env_var.to_dict()

    def delete(self, session: Session, envar_id: str) -> Dict[str, Any]:
        """Environment Variable silme"""
        # 1. VALIDATION: Environment Variable ID
        env_var = self.envar_crud.find_by_id(session, envar_id)
        if not env_var:
            raise BusinessLogicError(f"Environment variable not found: {envar_id}")
        
        # 2. OPERATION: Delete environment variable
        deleted_env_var = self.envar_crud.delete_env_var(session, envar_id)
        
        # 3. RETURN: API Format
        return deleted_env_var.to_dict()

    def search(self, session: Session, search_criteria: Dict[str, Any], skip: int = 0, limit: int = 100, order_by_field: str = None) -> Dict[str, Any]:
        """Environment Variable arama"""
        # 1. OPERATION: Search environment variables
        env_vars = self.envar_crud.filter(session, search_criteria, skip=skip, limit=limit, order_by_field=order_by_field)
        
        # Get total count for pagination
        total_count = self.envar_crud.count_filtered(session, search_criteria)
        
        # 2. RETURN: API Format
        return {
            'data': [env_var.to_dict() for env_var in env_vars],
            'total_count': total_count,
            'skip': skip,
            'limit': limit,
            'has_more': (skip + limit) < total_count
        }

    def get_all(self, session: Session) -> List[Dict[str, Any]]:
        """Tüm environment variable'ları getir"""
        env_vars = self.envar_crud.get_all(session)
        return [env_var.to_dict() for env_var in env_vars]

    def get(self, session: Session, envar_id: str, include_decrypted: bool = False) -> Dict[str, Any]:
        """Environment Variable detayını getir"""
        # 1. VALIDATION: Environment Variable ID
        env_var = self.envar_crud.find_by_id(session, envar_id)
        if not env_var:
            raise BusinessLogicError(f"Environment variable not found: {envar_id}")
        
        # 2. OPERATION: Get base env_var data
        env_var_dict = env_var.to_dict()
        
        # 3. OPERATION: Decrypt value if requested and encrypted
        if include_decrypted and env_var.is_encrypted:
            try:
                env_var_dict['decrypted_value'] = self._decrypt_value(env_var.value)
            except Exception:
                env_var_dict['decrypted_value'] = None
        
        # 4. RETURN: API Format
        return env_var_dict

    def count(self, session: Session) -> int:
        """Environment Variable sayısını getir"""
        return self.envar_crud.count(session)
    
    def exists(self, session: Session, envar_id: str) -> bool:
        """Environment Variable var mı kontrolü"""
        return self.envar_crud.exists(session, envar_id)

    def get_by_encrypted_status(self, session: Session, is_encrypted: bool) -> List[Dict[str, Any]]:
        """Şifreleme durumuna göre environment variable'ları getir"""
        env_vars = self.envar_crud.filter(session, {'is_encrypted': is_encrypted})
        return [env_var.to_dict() for env_var in env_vars]
    
    def get_encrypted_envars(self, session: Session) -> List[Dict[str, Any]]:
        """Şifrelenmiş environment variable'ları getir"""
        return self.get_by_encrypted_status(session, True)
    
    def get_unencrypted_envars(self, session: Session) -> List[Dict[str, Any]]:
        """Şifrelenmemiş environment variable'ları getir"""
        return self.get_by_encrypted_status(session, False)

    def _encrypt_value(self, value: str) -> str:
        """
        Encrypt environment variable value
        Note: This is a placeholder implementation.
        In production, use proper encryption like AES with a secure key management system.
        """
        if not value:
            return ""
        
        # This is a simple base64 encoding for demonstration
        # In real implementation, use proper encryption
        import base64
        try:
            return base64.b64encode(value.encode('utf-8')).decode('utf-8')
        except Exception:
            raise ValidationError("Failed to encrypt environment variable value")

    def _decrypt_value(self, encrypted_value: str) -> str:
        """
        Decrypt environment variable value
        Note: This is a placeholder implementation.
        """
        if not encrypted_value:
            return ""
        
        import base64
        try:
            return base64.b64decode(encrypted_value.encode('utf-8')).decode('utf-8')
        except Exception:
            raise ValidationError("Failed to decrypt environment variable value")