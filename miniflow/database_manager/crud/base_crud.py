"""
Generic base CRUD class for all entity-specific CRUD operations.
Provides type-safe CRUD operations with performance optimizations.
"""

from typing import Any, Dict, Generic, List, Optional, TypeVar, Union
from sqlalchemy import select, func, delete, update
from sqlalchemy.orm import DeclarativeMeta, Session

ModelType = TypeVar("ModelType", bound=DeclarativeMeta)


class BaseCRUD(Generic[ModelType]):
    """
    Generic base class for all entity CRUD operations.
    Provides type-safe CRUD operations with performance optimizations.
    """
    
    def __init__(self, model: type[ModelType]):
        self.model = model
        self.model_name = model.__name__

    # ==========================================================================
    # BASIC CRUD OPERATIONS
    # ==========================================================================

    def create(self, session: Session, **model_data) -> ModelType:
        """Create new model instance"""
        if not model_data:
            raise ValueError("No data provided for database insertion")

        db_object = self.model(**model_data)
        session.add(db_object)
        session.flush()
        return db_object
    
    def find_by_id(self, session: Session, record_id: Union[str, int]) -> Optional[ModelType]:
        """Find record by primary key"""
        result = session.get(self.model, record_id)
        if not result:
            raise ValueError(f"{self.model_name} not found: {record_id}")
        return result
    
    def find_by_name(self, session: Session, name: str) -> Optional[ModelType]:
        """Find record by name field"""
        if not hasattr(self.model, 'name'):
            raise ValueError(f"{self.model_name} does not have a 'name' field")
        
        stmt = select(self.model).where(self.model.name == name)
        result = session.execute(stmt).scalar_one_or_none()
        
        if not result:
            raise ValueError(f"{self.model_name} not found with name: {name}")
        return result
    
    def update(self, session: Session, record_id: Union[str, int], **model_data) -> ModelType:
        """Update existing record"""
        if not model_data:
            raise ValueError("No data provided for database update")
        
        db_object = self.find_by_id(session, record_id)
        
        for field, value in model_data.items():
            if hasattr(db_object, field):
                setattr(db_object, field, value)
        
        session.flush()
        return db_object

    def delete(self, session: Session, record_id: Union[str, int]) -> ModelType:
        """Delete existing record"""
        db_object = self.find_by_id(session, record_id)
        session.delete(db_object)
        session.flush()
        return db_object

    # ==========================================================================
    # QUERY OPERATIONS
    # ==========================================================================

    def get_all(self, session: Session, skip: int = 0, limit: int = 100, 
               order_by_field: str = None, desc: bool = False) -> List[ModelType]:
        """Memory-efficient pagination with optional ordering"""
        limit = min(limit, 1000)  # Memory protection
        
        stmt = select(self.model)
        
        # Ordering
        if order_by_field and hasattr(self.model, order_by_field):
            order_column = getattr(self.model, order_by_field)
            if desc:
                order_column = order_column.desc()
            stmt = stmt.order_by(order_column)
        else:
            stmt = stmt.order_by(self.model.id)  # Default ID ordering
        
        stmt = stmt.offset(skip).limit(limit)
        return list(session.execute(stmt).scalars().all())

    def count(self, session: Session) -> int:
        """Total record count"""
        stmt = select(func.count(self.model.id))
        return session.execute(stmt).scalar_one()

    def exists(self, session: Session, record_id: Union[str, int]) -> bool:
        """Check if record exists"""
        stmt = select(func.count(self.model.id)).where(self.model.id == record_id)
        return session.execute(stmt).scalar_one() > 0

    def filter(self, session: Session, filters: Dict[str, Any], 
              skip: int = 0, limit: int = 100, order_by_field: str = None) -> List[ModelType]:
        """Index-aware filtering with pagination"""
        limit = min(limit, 1000)  # Memory protection
        
        stmt = select(self.model)
        
        # Dynamic filter construction
        for field_name, field_value in filters.items():
            if hasattr(self.model, field_name):
                stmt = stmt.where(getattr(self.model, field_name) == field_value)
            else:
                raise ValueError(f"Field '{field_name}' does not exist in {self.model_name}")
        
        # Ordering
        if order_by_field and hasattr(self.model, order_by_field):
            stmt = stmt.order_by(getattr(self.model, order_by_field))
        else:
            stmt = stmt.order_by(self.model.id)
        
        stmt = stmt.offset(skip).limit(limit)
        return list(session.execute(stmt).scalars().all())

    def count_filtered(self, session: Session, filters: Dict[str, Any]) -> int:
        """Count filtered records"""
        stmt = select(func.count(self.model.id))
        
        for field_name, field_value in filters.items():
            if hasattr(self.model, field_name):
                stmt = stmt.where(getattr(self.model, field_name) == field_value)
            else:
                raise ValueError(f"Field '{field_name}' does not exist in {self.model_name}")
        
        return session.execute(stmt).scalar_one()

    def find_by_field(self, session: Session, field_name: str, value: Any, limit: int = 100) -> List[ModelType]:
        """Find records by single field value"""
        if not hasattr(self.model, field_name):
            raise ValueError(f"Field '{field_name}' does not exist in {self.model_name}")
        
        limit = min(limit, 1000)
        
        stmt = (
            select(self.model)
            .where(getattr(self.model, field_name) == value)
            .order_by(self.model.id)
            .limit(limit)
        )
        
        return list(session.execute(stmt).scalars().all())
    
    # ==========================================================================
    # BULK OPERATIONS
    # ==========================================================================

    def select_in_bulk(self, session: Session, ids: List[Union[str, int]]) -> List[ModelType]:
        """Bulk select by IDs"""
        if not ids:
            return []
        
        stmt = select(self.model).where(self.model.id.in_(ids))
        return list(session.execute(stmt).scalars().all())
    
    def truncate(self, session: Session) -> int:
        """Delete all records"""
        count = self.count(session)
        stmt = delete(self.model)
        session.execute(stmt)
        session.flush()
        return count
    
    def bulk_create(self, session: Session, objects_data: List[Dict[str, Any]]) -> int:
        """Bulk insert records"""
        if not objects_data:
            return 0
        
        session.bulk_insert_mappings(self.model, objects_data)
        session.flush()
        return len(objects_data)
    
    def bulk_update(self, session: Session, updates: List[Dict[str, Any]]) -> int:
        """Bulk update records (ID required in each update)"""
        if not updates:
            return 0
        
        for update_data in updates:
            if 'id' not in update_data:
                raise ValueError("'id' field is required for bulk update")
        
        session.bulk_update_mappings(self.model, updates)
        session.flush()
        return len(updates)
    
    def bulk_delete(self, session: Session, ids: List[Union[str, int]]) -> int:
        """Bulk delete by IDs"""
        if not ids:
            return 0
        
        stmt = delete(self.model).where(self.model.id.in_(ids))
        result = session.execute(stmt)
        session.flush()
        return result.rowcount or 0

    # ==========================================================================
    # OPTIMIZED OPERATIONS
    # ==========================================================================

    def check_name_exists(self, session: Session, name: str, exclude_id: str = None) -> bool:
        """Check if name exists (with optional exclude for updates)"""
        if not hasattr(self.model, 'name'):
            raise ValueError(f"{self.model_name} does not have a 'name' field")
        
        stmt = select(func.count(self.model.id)).where(self.model.name == name)
        
        if exclude_id:
            stmt = stmt.where(self.model.id != exclude_id)
        
        count = session.execute(stmt).scalar_one()
        return count > 0

    def bulk_update_status(self, session: Session, ids: List[Union[str, int]], 
                          status_field: str, new_status: Any) -> int:
        """Bulk update status field"""
        if not ids:
            return 0
        if not status_field:
            raise ValueError("Status field name is required")
        
        if not hasattr(self.model, status_field):
            raise ValueError(f"Field '{status_field}' does not exist in {self.model_name}")
        
        stmt = (
            update(self.model)
            .where(self.model.id.in_(ids))
            .values({status_field: new_status})
        )
        
        result = session.execute(stmt)
        session.flush()
        return result.rowcount or 0

    def bulk_update_fields(self, session: Session, ids: List[Union[str, int]], 
                          field_updates: Dict[str, Any]) -> int:
        """Bulk update multiple fields"""
        if not ids:
            return 0
        if not field_updates:
            raise ValueError("No field updates provided")
        
        for field_name in field_updates.keys():
            if not hasattr(self.model, field_name):
                raise ValueError(f"Field '{field_name}' does not exist in {self.model_name}")
        
        stmt = (
            update(self.model)
            .where(self.model.id.in_(ids))
            .values(field_updates)
        )
        
        result = session.execute(stmt)
        session.flush()
        return result.rowcount or 0