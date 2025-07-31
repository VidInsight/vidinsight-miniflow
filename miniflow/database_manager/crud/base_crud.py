"""
Base CRUD class providing generic type-safe database operations.
All entity-specific CRUD classes inherit from BaseCRUD[ModelType].
"""

from typing import Any, Dict, Generic, List, Optional, TypeVar, Union
from sqlalchemy import select, func, delete, update
from sqlalchemy.orm import DeclarativeMeta, Session

ModelType = TypeVar("ModelType", bound=DeclarativeMeta)

class BaseCRUD(Generic[ModelType]):
    """Generic base class for entity CRUD operations with type safety."""
    
    def __init__(self, model: type[ModelType]):
        """Initialize CRUD with SQLAlchemy model class."""
        self.model = model
        self.model_name = model.__name__

    # ==========================================================================
    # QUERY EXECUTION UTILITIES (NEW - ELIMINATES 24+ DUPLICATIONS)
    # Centralized query execution to eliminate return list(session.execute(stmt).scalars().all())
    # ==========================================================================
    
    def _execute_query_list(self, session: Session, stmt) -> List[ModelType]:
        """Centralized query execution for list results."""
        return list(session.execute(stmt).scalars().all())
    
    def _execute_query_first(self, session: Session, stmt) -> Optional[ModelType]:
        """Centralized query execution for single result"""
        return session.execute(stmt).scalars().first()
    
    # ==========================================================================
    # GENERIC QUERY METHODS (NEW - ELIMINATES 15+ get_by_X DUPLICATIONS)
    # Eliminate duplicate get_by_X patterns across all CRUD classes
    # ==========================================================================
    
    def get_by_field(self, session: Session, field_name: str, field_value: Any) -> List[ModelType]:
        """Generic field-based query for any model field."""
        if not hasattr(self.model, field_name):
            raise ValueError(f"Field '{field_name}' does not exist in {self.model_name}")
        
        stmt = select(self.model).where(getattr(self.model, field_name) == field_value)
        return self._execute_query_list(session, stmt)
    
    def get_by_workflow(self, session: Session, workflow_id: str) -> List[ModelType]:
        """Get entities by workflow_id."""
        return self.get_by_field(session, "workflow_id", workflow_id)
    
    def get_by_execution(self, session: Session, execution_id: str) -> List[ModelType]:
        """Get entities by execution_id."""
        return self.get_by_field(session, "execution_id", execution_id)
    
    def get_by_status(self, session: Session, status: Any) -> List[ModelType]:
        """Get entities by status."""
        return self.get_by_field(session, "status", status)

    # ==========================================================================
    # BASIC CRUD OPERATIONS
    # Temel Create, Read, Update, Delete işlemleri
    # ==========================================================================

    def create(self, session: Session, **model_data) -> ModelType:
        """
        Yeni model instance oluşturur ve database'e persist eder
        
        ALGORITHM:
        1. Model data validation
        2. Model instance oluştur
        3. Session'a add et
        4. Database'e flush et
        5. Created instance döndür
        
        Args:
            session (Session): Database session
            **model_data: Model field'ları ve değerleri
            
        Returns:
            ModelType: Oluşturulan model instance
            
        Raises:
            ValueError: Boş data sağlandığında
            
        Example:
            >>> workflow = crud.create(session, name="test", status="active")
        """
        # Step 1: Input validation
        if not model_data:
            raise ValueError("No data provided for database insertion")

        # Step 2: Model instance oluştur
        db_object = self.model(**model_data)
        
        # Step 3: Session'a add et (pending state)
        session.add(db_object)
        
        # Step 4: Database'e flush et (ID generate edilir)
        session.flush()
        
        # Step 5: Created instance döndür
        return db_object
    
    def find_by_id(self, session: Session, record_id: Union[str, int]) -> Optional[ModelType]:
        """
        Primary key ile single record retrieve eder
        
        ALGORITHM:
        1. Session.get() ile efficient primary key lookup
        2. Record existence validation
        3. Found record döndür veya exception fırlat
        
        Args:
            session (Session): Database session
            record_id (Union[str, int]): Primary key değeri
            
        Returns:
            ModelType: Bulunan model instance
            
        Raises:
            ValueError: Record bulunamadığında
            
        Example:
            >>> workflow = crud.find_by_id(session, "uuid-string")
        """
        # Step 1: Efficient primary key lookup
        result = session.get(self.model, record_id)
        
        # Step 2: Existence validation
        if not result:
            raise ValueError(f"{self.model_name} not found: {record_id}")
            
        # Step 3: Found record döndür
        return result
    
    def find_by_name(self, session: Session, name: str) -> Optional[ModelType]:
        """
        Name field ile single record retrieve eder
        
        ALGORITHM:
        1. Model'in name field'ı olduğunu validate et
        2. Name-based query execute et
        3. Single result extract et
        4. Found record döndür veya exception fırlat
        
        Args:
            session (Session): Database session
            name (str): Name field değeri
            
        Returns:
            ModelType: Bulunan model instance
            
        Raises:
            ValueError: Model'de name field yoksa veya record bulunamadığında
            
        Example:
            >>> workflow = crud.find_by_name(session, "my-workflow")
        """
        # Step 1: Name field existence validation
        if not hasattr(self.model, 'name'):
            raise ValueError(f"{self.model_name} does not have a 'name' field")
        
        # Step 2: Name-based query construction
        stmt = select(self.model).where(self.model.name == name)
        
        # Step 3: Single result extraction
        result = session.execute(stmt).scalar_one_or_none()
        
        # Step 4: Existence validation
        if not result:
            raise ValueError(f"{self.model_name} not found with name: {name}")
            
        return result
    
    def update(self, session: Session, record_id: Union[str, int], **model_data) -> ModelType:
        """
        Existing record'u update eder
        
        ALGORITHM:
        1. Update data validation
        2. Record existence verification
        3. Field'ları iterate et ve update et
        4. Database'e flush et
        5. Updated instance döndür
        
        Args:
            session (Session): Database session
            record_id (Union[str, int]): Update edilecek record ID
            **model_data: Update edilecek field'lar ve değerleri
            
        Returns:
            ModelType: Update edilmiş model instance
            
        Raises:
            ValueError: Boş data veya record bulunamadığında
            
        Example:
            >>> workflow = crud.update(session, "uuid", status="inactive")
        """
        # Step 1: Update data validation
        if not model_data:
            raise ValueError("No data provided for database update")
        
        # Step 2: Record existence verification
        db_object = self.find_by_id(session, record_id)
        
        # Step 3: Field iteration ve update
        for field, value in model_data.items():
            if hasattr(db_object, field):
                setattr(db_object, field, value)
        
        # Step 4: Database flush
        session.flush()
        
        # Step 5: Updated instance döndür
        return db_object

    def delete(self, session: Session, record_id: Union[str, int]) -> ModelType:
        """
        Existing record'u delete eder
        
        ALGORITHM:
        1. Record existence verification
        2. Session'dan delete et
        3. Database'e flush et
        4. Deleted instance döndür
        
        Args:
            session (Session): Database session
            record_id (Union[str, int]): Delete edilecek record ID
            
        Returns:
            ModelType: Delete edilmiş model instance
            
        Raises:
            ValueError: Record bulunamadığında
            
        Example:
            >>> deleted_workflow = crud.delete(session, "uuid")
        """
        # Step 1: Record existence verification
        db_object = self.find_by_id(session, record_id)
        
        # Step 2: Session'dan delete et
        session.delete(db_object)
        
        # Step 3: Database flush
        session.flush()
        
        # Step 4: Deleted instance döndür
        return db_object

    # ==========================================================================
    # QUERY OPERATIONS
    # Gelişmiş query ve filtering operasyonları
    # ==========================================================================

    def get_all(self, session: Session, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """
        Pagination ile tüm record'ları retrieve eder
        
        Args:
            session (Session): Database session
            skip (int): Skip edilecek record sayısı (offset)
            limit (int): Maksimum return edilecek record sayısı
            
        Returns:
            List[ModelType]: Paginated record list
        """
        stmt = select(self.model).offset(skip).limit(limit)
        return list(session.execute(stmt).scalars().all())

    def count(self, session: Session) -> int:
        """
        Total record count döndürür
        
        Args:
            session (Session): Database session
            
        Returns:
            int: Total record sayısı
        """
        stmt = select(func.count(self.model.id))
        return session.execute(stmt).scalar_one()

    def exists(self, session: Session, record_id: Union[str, int]) -> bool:
        """
        Record existence check eder
        
        Args:
            session (Session): Database session
            record_id (Union[str, int]): Check edilecek record ID
            
        Returns:
            bool: Record var ise True, yoksa False
        """
        stmt = select(func.count(self.model.id)).where(self.model.id == record_id)
        return session.execute(stmt).scalar_one() > 0

    def filter(self, session: Session, filters: Dict[str, Any], skip: int = 0, limit: int = 100) -> List[ModelType]:
        """
        Dinamik filtering ile record'ları retrieve eder
        
        Args:
            session (Session): Database session
            filters (Dict[str, Any]): Field name → value mapping
            skip (int): Pagination offset
            limit (int): Pagination limit
            
        Returns:
            List[ModelType]: Filtered record list
            
        Raises:
            ValueError: Geçersiz field name'de
        """
        stmt = select(self.model)
        
        # Dynamic filter construction
        for field_name, field_value in filters.items():
            if hasattr(self.model, field_name):
                stmt = stmt.where(getattr(self.model, field_name) == field_value)
            else:
                raise ValueError(f"Field '{field_name}' does not exist in {self.model_name}")
        
        # Pagination
        stmt = stmt.offset(skip).limit(limit)
        return list(session.execute(stmt).scalars().all())

    def order_by(self, session: Session, order_field: str, desc: bool = False, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """
        Sorting ile record'ları retrieve eder
        
        Args:
            session (Session): Database session
            order_field (str): Sort edilecek field name
            desc (bool): Descending order flag
            skip (int): Pagination offset
            limit (int): Pagination limit
            
        Returns:
            List[ModelType]: Sorted record list
            
        Raises:
            ValueError: Geçersiz field name'de
        """
        # Field existence validation
        if not hasattr(self.model, order_field):
            raise ValueError(f"Field '{order_field}' does not exist in {self.model_name}")
        
        # Order column construction
        order_column = getattr(self.model, order_field)
        if desc:
            order_column = order_column.desc()
        
        # Query with ordering and pagination
        stmt = select(self.model).order_by(order_column).offset(skip).limit(limit)
        return list(session.execute(stmt).scalars().all())
    
    # ==========================================================================
    # BULK OPERATIONS
    # Performance-optimized mass operations
    # ==========================================================================

    def select_in_bulk(self, session: Session, ids: List[Union[str, int]]) -> List[ModelType]:
        """
        Multiple ID ile bulk record retrieve
        
        Args:
            session (Session): Database session
            ids (List[Union[str, int]]): Record ID list
            
        Returns:
            List[ModelType]: Bulunan record'lar
        """
        if not ids:
            return []
        
        stmt = select(self.model).where(self.model.id.in_(ids))
        return list(session.execute(stmt).scalars().all())
    
    def truncate(self, session: Session) -> int:
        """
        Tüm record'ları delete eder ve count döndürür
        
        Args:
            session (Session): Database session
            
        Returns:
            int: Silinen record sayısı
        """
        # Current count
        count = self.count(session)
        
        # Bulk delete
        stmt = delete(self.model)
        session.execute(stmt)
        session.flush()
        
        return count
    
    def bulk_create(self, session: Session, objects_data: List[Dict[str, Any]]) -> int:
        """
        Single SQL statement ile multiple record create
        
        Args:
            session (Session): Database session
            objects_data (List[Dict[str, Any]]): Create edilecek record data list
            
        Returns:
            int: Create edilen record sayısı
        """
        if not objects_data:
            return 0
        
        # SQLAlchemy bulk insert
        session.bulk_insert_mappings(self.model, objects_data)
        session.flush()
        
        return len(objects_data)
    
    def bulk_update(self, session: Session, updates: List[Dict[str, Any]]) -> int:
        """
        Single SQL statement ile multiple record update
        
        Args:
            session (Session): Database session
            updates (List[Dict[str, Any]]): Update data list (ID required)
            
        Returns:
            int: Update edilen record sayısı
            
        Raises:
            ValueError: ID field missing'de
        """
        if not updates:
            return 0
        
        # ID field validation
        for update_data in updates:
            if 'id' not in update_data:
                raise ValueError("'id' field is required for bulk update")
        
        # SQLAlchemy bulk update
        session.bulk_update_mappings(self.model, updates)
        session.flush()
        
        return len(updates)
    
    def bulk_delete(self, session: Session, ids: List[Union[str, int]]) -> int:
        """
        Single SQL statement ile multiple record delete
        
        Args:
            session (Session): Database session
            ids (List[Union[str, int]]): Delete edilecek record ID list
            
        Returns:
            int: Delete edilen record sayısı
        """
        if not ids:
            return 0
        
        # SQLAlchemy bulk delete
        stmt = delete(self.model).where(self.model.id.in_(ids))
        result = session.execute(stmt)
        session.flush()
        
        deleted_count = result.rowcount or 0
        return deleted_count