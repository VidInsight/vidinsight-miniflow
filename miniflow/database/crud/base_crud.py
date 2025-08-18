from typing import Any, Dict, Generic, List, Optional, TypeVar, Union
from sqlalchemy import select, func, delete, update
from sqlalchemy.orm import DeclarativeMeta, Session
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timezone
import logging

from ...exceptions import CRUDException, DatabaseError, ValidationError


ModelType = TypeVar("ModelType", bound=DeclarativeMeta)


class BaseCRUD(Generic[ModelType]):
    """
    Tüm varlıklar için CRUD işlemleri için genel temel sınıf.
    Performans optimizasyonlarıyla tip güvenli CRUD işlemleri sağlar.
    
    Note: Bu sınıf DatabaseEngine'in session context management yapısı ile çalışır.
    Session rollback işlemleri engine seviyesinde handle edilir.
    """

    def __init__(self, model: type[ModelType]):
        """Initialize BaseCRUD with the specific model type for type-safe operations."""
        self.model = model
        self.model_name = model.__name__
        self.logger = logging.getLogger(f"{__name__}.{self.model_name}")

    def create(self, session: Session, **model_data) -> ModelType:
        """Create new database record with automatic field validation."""
        if not model_data:
            raise ValidationError(f"No data provided for {self.model_name} creation")

        # Filter out invalid fields that don't exist in the model
        valid_data = {}
        for field, value in model_data.items():
            if hasattr(self.model, field):
                valid_data[field] = value
            else:
                self.logger.warning(f"Ignoring invalid field '{field}' for {self.model_name}")
        
        try:
            self.logger.debug(f"Creating {self.model_name} with data: {list(valid_data.keys())}")
            db_object = self.model(**valid_data)
            session.add(db_object)
            session.flush()
            self.logger.info(f"Successfully created {self.model_name} with ID: {getattr(db_object, 'id', 'N/A')}")
            return db_object
        except SQLAlchemyError as e:
            self.logger.error(f"Database error creating {self.model_name}: {str(e)}")
            raise DatabaseError(f"Failed to create {self.model_name}", str(e))
        except Exception as e:
            self.logger.error(f"Unexpected error creating {self.model_name}: {str(e)}")
            raise CRUDException(f"Object Creation Error: {self.model_name}: {str(e)}")

    def find_by_id(self, session: Session, record_id: Union[str, int]) -> Optional[ModelType]:
        """Find single record by primary key ID."""
        if record_id is None:
            raise ValidationError("Record ID cannot be None")
            
        try:
            self.logger.debug(f"Finding {self.model_name} by ID: {record_id}")
            result = session.get(self.model, record_id)
            if result:
                self.logger.debug(f"Found {self.model_name} with ID: {record_id}")
            else:
                self.logger.debug(f"No {self.model_name} found with ID: {record_id}")
            return result
        except SQLAlchemyError as e:
            self.logger.error(f"Database error finding {self.model_name} by ID {record_id}: {str(e)}")
            raise DatabaseError(f"Failed to find {self.model_name} by ID", str(e))
        except Exception as e:
            self.logger.error(f"Unexpected error finding {self.model_name} by ID {record_id}: {str(e)}")
            raise CRUDException(f"Object Retrieval Error (via ID): {self.model_name}: {str(e)}")

    def find_by_name(self, session: Session, record_name: str) -> Optional[ModelType]:
        """Find single record by name field (if model has name attribute)."""
        if not record_name or not record_name.strip():
            raise ValidationError("Record name cannot be empty")
            
        if not hasattr(self.model, 'name'):
            raise ValidationError(f"{self.model_name} does not have a 'name' field")

        try:
            self.logger.debug(f"Finding {self.model_name} by name: {record_name}")
            stmt = select(self.model).where(self.model.name == record_name)
            result = session.execute(stmt).scalar_one_or_none()
            if result:
                self.logger.debug(f"Found {self.model_name} with name: {record_name}")
            else:
                self.logger.debug(f"No {self.model_name} found with name: {record_name}")
            return result
        except SQLAlchemyError as e:
            self.logger.error(f"Database error finding {self.model_name} by name {record_name}: {str(e)}")
            raise DatabaseError(f"Failed to find {self.model_name} by name", str(e))
        except Exception as e:
            self.logger.error(f"Unexpected error finding {self.model_name} by name {record_name}: {str(e)}")
            raise CRUDException(f"Object Retrieval Error (via name): {self.model_name}: {str(e)}")


    def update(self, session: Session, record_id: Union[str, int], **model_data) -> ModelType:
        """Update existing record with automatic timestamp and field validation."""
        if not model_data:
            raise ValidationError(f"No data provided for {self.model_name} update")
        
        db_object = self.find_by_id(session, record_id)
        if db_object is None:
            raise CRUDException(f"Object Update Error: No such {self.model_name} record with ID {record_id}")

        # Add timestamp if model supports it
        if hasattr(db_object, 'updated_at'):
            model_data['updated_at'] = datetime.now(timezone.utc)

        try:
            self.logger.debug(f"Updating {self.model_name} ID {record_id} with data: {list(model_data.keys())}")
            updated_fields = []
            for field, value in model_data.items():
                if hasattr(db_object, field):
                    setattr(db_object, field, value)
                    updated_fields.append(field)
                else:
                    self.logger.warning(f"Ignoring invalid field '{field}' for {self.model_name} update")
            
            session.flush()
            self.logger.info(f"Successfully updated {self.model_name} ID {record_id}, fields: {updated_fields}")
            return db_object
        except SQLAlchemyError as e:
            self.logger.error(f"Database error updating {self.model_name} ID {record_id}: {str(e)}")
            raise DatabaseError(f"Failed to update {self.model_name}", str(e))
        except Exception as e:
            self.logger.error(f"Unexpected error updating {self.model_name} ID {record_id}: {str(e)}")
            raise CRUDException(f"Object Update Error: {self.model_name}: {str(e)}")

    def delete(self, session: Session, record_id: Union[str, int]) -> ModelType:
        """Delete record by ID and return the deleted object."""
        db_object = self.find_by_id(session, record_id)
        if db_object is None:
            raise CRUDException(f"Object Deletion Error: No such {self.model_name} record with ID {record_id}")

        try:
            self.logger.debug(f"Deleting {self.model_name} ID {record_id}")
            session.delete(db_object)
            session.flush()
            self.logger.info(f"Successfully deleted {self.model_name} ID {record_id}")
            return db_object
        except SQLAlchemyError as e:
            self.logger.error(f"Database error deleting {self.model_name} ID {record_id}: {str(e)}")
            raise DatabaseError(f"Failed to delete {self.model_name}", str(e))
        except Exception as e:
            self.logger.error(f"Unexpected error deleting {self.model_name} ID {record_id}: {str(e)}")
            raise CRUDException(f"Object Deletion Error: {self.model_name}: {str(e)}")

    def get_all(self, session: Session, skip: int = 0, limit: int = 100, order_by: str = None) -> List[ModelType]:
        """Get all records with pagination and optional ordering."""
        if skip < 0:
            raise ValidationError("Skip value cannot be negative")
        if limit <= 0:
            raise ValidationError("Limit value must be positive")
            
        limit = min(limit, 1000)  # Memory protection
        stmt = select(self.model)

        if order_by:
            if hasattr(self.model, order_by):
                order_column = getattr(self.model, order_by)
                stmt = stmt.order_by(order_column)
            else:
                self.logger.warning(f"Invalid order_by field '{order_by}' for {self.model_name}, using default ID ordering")
                stmt = stmt.order_by(self.model.id)
        else:
            stmt = stmt.order_by(self.model.id)  # Default ID ordering
        
        stmt = stmt.offset(skip).limit(limit)
        try:
            self.logger.debug(f"Getting all {self.model_name} records: skip={skip}, limit={limit}, order_by={order_by}")
            results = list(session.execute(stmt).scalars().all())
            self.logger.debug(f"Retrieved {len(results)} {self.model_name} records")
            return results
        except SQLAlchemyError as e:
            self.logger.error(f"Database error getting all {self.model_name} records: {str(e)}")
            raise DatabaseError(f"Failed to retrieve {self.model_name} records", str(e))
        except Exception as e:
            self.logger.error(f"Unexpected error getting all {self.model_name} records: {str(e)}")
            raise CRUDException(f"Object Retrieval Error (via Get All): {self.model_name}: {str(e)}")

    def count(self, session: Session) -> int:
        """Count total number of records in the table."""
        stmt = select(func.count(self.model.id))
        try:
            self.logger.debug(f"Counting {self.model_name} records")
            result = session.execute(stmt).scalar_one()
            self.logger.debug(f"Total {self.model_name} count: {result}")
            return result
        except SQLAlchemyError as e:
            self.logger.error(f"Database error counting {self.model_name} records: {str(e)}")
            raise DatabaseError(f"Failed to count {self.model_name} records", str(e))
        except Exception as e:
            self.logger.error(f"Unexpected error counting {self.model_name} records: {str(e)}")
            raise CRUDException(f"Object Count Error: {self.model_name}: {str(e)}")

    def exists(self, session: Session, record_id: Union[str, int]) -> bool:
        """Check if record exists by ID."""
        if record_id is None:
            raise ValidationError("Record ID cannot be None")
            
        stmt = select(func.count(self.model.id)).where(self.model.id == record_id)
        try:
            self.logger.debug(f"Checking if {self.model_name} exists with ID: {record_id}")
            result = session.execute(stmt).scalar_one() > 0
            self.logger.debug(f"{self.model_name} ID {record_id} exists: {result}")
            return result
        except SQLAlchemyError as e:
            self.logger.error(f"Database error checking {self.model_name} existence ID {record_id}: {str(e)}")
            raise DatabaseError(f"Failed to check {self.model_name} existence", str(e))
        except Exception as e:
            self.logger.error(f"Unexpected error checking {self.model_name} existence ID {record_id}: {str(e)}")
            raise CRUDException(f"Object Exists Error: {self.model_name}: {str(e)}")

    def filter(self, session: Session, filters: Dict[str, Any], skip: int = 0, limit: int = 100, order_by_field: str = None) -> List[ModelType]:
        """Filter records by field values with pagination and ordering."""
        if not filters:
            raise ValidationError("Filter criteria cannot be empty")
        if skip < 0:
            raise ValidationError("Skip value cannot be negative")
        if limit <= 0:
            raise ValidationError("Limit value must be positive")
            
        limit = min(limit, 1000)  # Memory protection
        stmt = select(self.model)

        valid_filters = []
        for field_name, field_value in filters.items():
            if hasattr(self.model, field_name):
                stmt = stmt.where(getattr(self.model, field_name) == field_value)
                valid_filters.append(f"{field_name}={field_value}")
            else:
                raise ValidationError(f"Field '{field_name}' does not exist in {self.model_name}")

        if order_by_field:
            if hasattr(self.model, order_by_field):
                stmt = stmt.order_by(getattr(self.model, order_by_field))
            else:
                self.logger.warning(f"Invalid order_by_field '{order_by_field}' for {self.model_name}, using default ID ordering")
                stmt = stmt.order_by(self.model.id)
        else:
            stmt = stmt.order_by(self.model.id)

        stmt = stmt.offset(skip).limit(limit)

        try:
            self.logger.debug(f"Filtering {self.model_name} records: {valid_filters}, skip={skip}, limit={limit}")
            results = list(session.execute(stmt).scalars().all())
            self.logger.debug(f"Filter returned {len(results)} {self.model_name} records")
            return results
        except SQLAlchemyError as e:
            self.logger.error(f"Database error filtering {self.model_name} records: {str(e)}")
            raise DatabaseError(f"Failed to filter {self.model_name} records", str(e))
        except Exception as e:
            self.logger.error(f"Unexpected error filtering {self.model_name} records: {str(e)}")
            raise CRUDException(f"Object Retrieval Error (via Filter): {self.model_name}: {str(e)}")

    def count_filtered(self, session: Session, filters: Dict[str, Any]) -> int:
        """Count records matching the specified filter criteria."""
        if not filters:
            raise ValidationError("Filter criteria cannot be empty")
            
        stmt = select(func.count(self.model.id))
        valid_filters = []

        for field_name, field_value in filters.items():
            if hasattr(self.model, field_name):
                stmt = stmt.where(getattr(self.model, field_name) == field_value)
                valid_filters.append(f"{field_name}={field_value}")
            else:
                raise ValidationError(f"Field '{field_name}' does not exist in {self.model_name}")

        try:
            self.logger.debug(f"Counting filtered {self.model_name} records: {valid_filters}")
            result = session.execute(stmt).scalar_one()
            self.logger.debug(f"Filtered {self.model_name} count: {result}")
            return result
        except SQLAlchemyError as e:
            self.logger.error(f"Database error counting filtered {self.model_name} records: {str(e)}")
            raise DatabaseError(f"Failed to count filtered {self.model_name} records", str(e))
        except Exception as e:
            self.logger.error(f"Unexpected error counting filtered {self.model_name} records: {str(e)}")
            raise CRUDException(f"Object Count Error (via Count Filtered): {self.model_name}: {str(e)}")

    def select_in_bulk(self, session: Session, ids: List[Union[str, int]]) -> List[ModelType]:
        """Select multiple records by ID list in a single query."""
        if not ids:
            raise ValidationError("ID list cannot be empty")
        if None in ids:
            raise ValidationError("ID list cannot contain None values")
            
        stmt = select(self.model).where(self.model.id.in_(ids))

        try:
            self.logger.debug(f"Bulk selecting {self.model_name} records: {len(ids)} IDs")
            results = list(session.execute(stmt).scalars().all())
            self.logger.debug(f"Bulk select returned {len(results)} {self.model_name} records")
            return results
        except SQLAlchemyError as e:
            self.logger.error(f"Database error bulk selecting {self.model_name} records: {str(e)}")
            raise DatabaseError(f"Failed to bulk select {self.model_name} records", str(e))
        except Exception as e:
            self.logger.error(f"Unexpected error bulk selecting {self.model_name} records: {str(e)}")
            raise CRUDException(f"Object Retrieval Error (via Select in Bulk): {self.model_name}: {str(e)}")

    def truncate(self, session: Session) -> int:
        """Delete all records from the table and return count of deleted records."""
        try:
            count = self.count(session)
            self.logger.warning(f"Truncating all {self.model_name} records: {count} records will be deleted")
            
            stmt = delete(self.model)
            session.execute(stmt)
            session.flush()
            
            self.logger.info(f"Successfully truncated {count} {self.model_name} records")
            return count
        except SQLAlchemyError as e:
            self.logger.error(f"Database error truncating {self.model_name} table: {str(e)}")
            raise DatabaseError(f"Failed to truncate {self.model_name} table", str(e))
        except Exception as e:
            self.logger.error(f"Unexpected error truncating {self.model_name} table: {str(e)}")
            raise CRUDException(f"Object Deletion Error (via Truncate): {self.model_name}: {str(e)}")

    def bulk_create(self, session: Session, objects_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create multiple records in a single operation with automatic ID generation."""
        if not objects_data:
            raise ValidationError("Objects data list cannot be empty")

        try:
            self.logger.debug(f"Bulk creating {len(objects_data)} {self.model_name} records")
            
            # ID'leri otomatik olarak ekle
            for i, obj_data in enumerate(objects_data):
                if not obj_data:
                    raise ValidationError(f"Object data at index {i} cannot be empty")
                    
                if 'id' not in obj_data or obj_data['id'] is None:
                    # BaseModel'in ID generation metodunu kullan
                    if hasattr(self.model, '_generate_id'):
                        obj_data['id'] = self.model._generate_id()
                    else:
                        # Fallback: basit UUID
                        raise ValidationError(f"ID generation method not found (bulk_create): {self.model_name}")

            session.bulk_insert_mappings(self.model, objects_data)
            session.flush()
            
            self.logger.info(f"Successfully bulk created {len(objects_data)} {self.model_name} records")
            return objects_data
        except SQLAlchemyError as e:
            self.logger.error(f"Database error bulk creating {self.model_name} records: {str(e)}")
            raise DatabaseError(f"Failed to bulk create {self.model_name} records", str(e))
        except Exception as e:
            self.logger.error(f"Unexpected error bulk creating {self.model_name} records: {str(e)}")
            raise CRUDException(f"Bulk Creation Error: {self.model_name}: {str(e)}")

    def bulk_update(self, session: Session, updates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Update multiple records in a single operation using ID for matching."""
        if not updates:
            raise ValidationError("Updates list cannot be empty")

        try:
            self.logger.debug(f"Bulk updating {len(updates)} {self.model_name} records")
            
            for i, update_data in enumerate(updates):
                if not update_data:
                    raise ValidationError(f"Update data at index {i} cannot be empty")
                if 'id' not in update_data:
                    raise ValidationError(f"'id' field is required for bulk update at index {i}")
                if update_data['id'] is None:
                    raise ValidationError(f"'id' field cannot be None at index {i}")

            session.bulk_update_mappings(self.model, updates)
            session.flush()
            
            self.logger.info(f"Successfully bulk updated {len(updates)} {self.model_name} records")
            return updates
        except SQLAlchemyError as e:
            self.logger.error(f"Database error bulk updating {self.model_name} records: {str(e)}")
            raise DatabaseError(f"Failed to bulk update {self.model_name} records", str(e))
        except Exception as e:
            self.logger.error(f"Unexpected error bulk updating {self.model_name} records: {str(e)}")
            raise CRUDException(f"Bulk Update Error: {self.model_name}: {str(e)}")

    def bulk_delete(self, session: Session, ids: List[Union[str, int]]) -> int:
        """Delete multiple records by ID list and return count of deleted records."""
        if not ids:
            raise ValidationError("ID list cannot be empty")
        if None in ids:
            raise ValidationError("ID list cannot contain None values")

        try:
            self.logger.debug(f"Bulk deleting {len(ids)} {self.model_name} records")
            
            stmt = delete(self.model).where(self.model.id.in_(ids))
            result = session.execute(stmt)
            session.flush()
            
            deleted_count = result.rowcount or 0
            self.logger.info(f"Successfully bulk deleted {deleted_count} {self.model_name} records")
            return deleted_count
        except SQLAlchemyError as e:
            self.logger.error(f"Database error bulk deleting {self.model_name} records: {str(e)}")
            raise DatabaseError(f"Failed to bulk delete {self.model_name} records", str(e))
        except Exception as e:
            self.logger.error(f"Unexpected error bulk deleting {self.model_name} records: {str(e)}")
            raise CRUDException(f"Bulk Deletion Error: {self.model_name}: {str(e)}")

    def bulk_update_status(self, session: Session, ids: List[Union[str, int]],
                          status_field: str, new_status: Any) -> int:
        """Update status field for multiple records and return count of updated records."""
        if not ids:
            raise ValidationError("ID list cannot be empty")
        if None in ids:
            raise ValidationError("ID list cannot contain None values")
        if not status_field or not status_field.strip():
            raise ValidationError("Status field name is required")
        if new_status is None:
            raise ValidationError("New status cannot be None")

        if not hasattr(self.model, status_field):
            raise ValidationError(f"Field '{status_field}' does not exist in {self.model_name}")

        try:
            self.logger.debug(f"Bulk updating {status_field} to {new_status} for {len(ids)} {self.model_name} records")
            
            stmt = (
                update(self.model)
                .where(self.model.id.in_(ids))
                .values({status_field: new_status})
            )

            result = session.execute(stmt)
            session.flush()
            
            updated_count = result.rowcount or 0
            self.logger.info(f"Successfully bulk updated {status_field} for {updated_count} {self.model_name} records")
            return updated_count
        except SQLAlchemyError as e:
            self.logger.error(f"Database error bulk updating {status_field} for {self.model_name} records: {str(e)}")
            raise DatabaseError(f"Failed to bulk update {status_field} for {self.model_name} records", str(e))
        except Exception as e:
            self.logger.error(f"Unexpected error bulk updating {status_field} for {self.model_name} records: {str(e)}")
            raise CRUDException(f"Bulk Status Update Error: {self.model_name}: {str(e)}")

    def bulk_update_fields(self, session: Session, ids: List[Union[str, int]],
                          field_updates: Dict[str, Any]) -> int:
        """Update multiple fields for multiple records and return count of updated records."""
        if not ids:
            raise ValidationError("ID list cannot be empty")
        if None in ids:
            raise ValidationError("ID list cannot contain None values")
        if not field_updates:
            raise ValidationError("No field updates provided")

        valid_fields = []
        for field_name in field_updates.keys():
            if not hasattr(self.model, field_name):
                raise ValidationError(f"Field '{field_name}' does not exist in {self.model_name}")
            valid_fields.append(field_name)

        try:
            self.logger.debug(f"Bulk updating fields {valid_fields} for {len(ids)} {self.model_name} records")
            
            stmt = (
                update(self.model)
                .where(self.model.id.in_(ids))
                .values(field_updates)
            )

            result = session.execute(stmt)
            session.flush()
            
            updated_count = result.rowcount or 0
            self.logger.info(f"Successfully bulk updated fields {valid_fields} for {updated_count} {self.model_name} records")
            return updated_count
        except SQLAlchemyError as e:
            self.logger.error(f"Database error bulk updating fields for {self.model_name} records: {str(e)}")
            raise DatabaseError(f"Failed to bulk update fields for {self.model_name} records", str(e))
        except Exception as e:
            self.logger.error(f"Unexpected error bulk updating fields for {self.model_name} records: {str(e)}")
            raise CRUDException(f"Bulk Fields Update Error: {self.model_name}: {str(e)}")