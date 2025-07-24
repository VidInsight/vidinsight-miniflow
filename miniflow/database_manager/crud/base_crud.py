"""
BASE CRUD MODULE
================

Bu modül tüm entity-specific CRUD sınıfları için ortak base class sağlar.
Generic type programming kullanarak type-safe ve reusable CRUD operations
implement eder. Her CRUD sınıfı bu base'den inherit ederek common functionality
kazanır ve entity-specific methods ekleyebilir.

MODÜL SORUMLULUKLARI:
====================
1. Generic CRUD Operations - Create, Read, Update, Delete
2. Type Safety - Generic type programming ile compile-time safety
3. Common Query Patterns - Filtering, ordering, pagination
4. Bulk Operations - Performance-optimized mass operations
5. Error Handling - Consistent error handling patterns

BASE CRUD ARCHITECTURE:
=======================
┌─────────────────────────────────────────────────────────┐
│                    BaseCRUD<T>                         │
├─────────────────────────────────────────────────────────┤
│  BASIC CRUD OPERATIONS:                                │
│  • create(session, **data) → T                        │
│  • find_by_id(session, id) → T                        │
│  • find_by_name(session, name) → T                    │
│  • update(session, id, **data) → T                    │
│  • delete(session, id) → T                            │
├─────────────────────────────────────────────────────────┤
│  QUERY OPERATIONS:                                     │
│  • get_all(session, skip, limit) → List[T]            │
│  • count(session) → int                               │
│  • exists(session, id) → bool                         │
│  • filter(session, filters, skip, limit) → List[T]   │
│  • order_by(session, field, desc, skip, limit) → List[T] │
├─────────────────────────────────────────────────────────┤
│  BULK OPERATIONS:                                      │
│  • select_in_bulk(session, ids) → List[T]             │
│  • bulk_create(session, data_list) → int              │
│  • bulk_update(session, updates) → int                │
│  • bulk_delete(session, ids) → int                    │
│  • truncate(session) → int                            │
└─────────────────────────────────────────────────────────┘

TYPE SAFETY:
============
Generic type parameter T, SQLAlchemy model türünü represent eder:
- T: ModelType (Workflow, Node, Execution, etc.)
- Compile-time type checking sağlar
- IDE autocomplete ve IntelliSense desteği
- Runtime type validation

INHERITANCE PATTERN:
===================
```python
class WorkflowCRUD(BaseCRUD[Workflow]):
    def __init__(self):
        super().__init__(Workflow)
    
    # Entity-specific methods
    def get_active_workflows(self, session: Session) -> List[Workflow]:
        return self.filter(session, {"status": "active"})
```

PERFORMANCE FEATURES:
====================
• Bulk Operations: Single SQL statement ile multiple records
• Query Optimization: Index-aware query patterns
• Lazy Loading: Efficient relationship loading
• Connection Reuse: Session-based operation batching
• Memory Efficiency: Streaming large result sets

ERROR HANDLING PATTERNS:
========================
• ValueError: Invalid input parameters
• RuntimeError: Database operation failures  
• Custom Exceptions: Business logic violations
• Consistent error messages with context
"""

from typing import Any, Dict, Generic, List, Optional, TypeVar, Union
from sqlalchemy import select, func, delete, update
from sqlalchemy.orm import DeclarativeMeta, Session

# =============================================================================
# TYPE DEFINITIONS
# Generic type programming için type definitions
# =============================================================================

ModelType = TypeVar("ModelType", bound=DeclarativeMeta)
"""
Generic type variable SQLAlchemy model'larını represent eder

Bu type variable tüm SQLAlchemy DeclarativeMeta subclass'larını accept eder:
- Workflow, Node, Execution, etc.
- Compile-time type safety sağlar
- IDE support ve autocomplete enable eder

Example:
    BaseCRUD[Workflow] → ModelType = Workflow
    BaseCRUD[Node] → ModelType = Node
"""

# =============================================================================
# BASE CRUD CLASS
# Generic CRUD operations için ana base sınıf
# =============================================================================

class BaseCRUD(Generic[ModelType]):
    """
    Tüm entity CRUD sınıfları için generic base class
    
    Bu class generic type programming kullanarak type-safe CRUD operations
    sağlar. Her concrete CRUD sınıfı bu base'den inherit ederek:
    - Common CRUD functionality kazanır
    - Entity-specific methods ekleyebilir
    - Type safety ve IDE support benefit eder
    
    GENERIC TYPE PARAMETER:
    ======================
    ModelType: SQLAlchemy model class (Workflow, Node, etc.)
    
    INSTANCE ATTRIBUTES:
    ===================
    • model: SQLAlchemy model class reference
    • model_name: Model class adı (debugging için)
    
    OPERATION CATEGORIES:
    ====================
    1. Basic CRUD: create, read, update, delete
    2. Query Operations: filtering, ordering, pagination
    3. Bulk Operations: mass insert/update/delete
    4. Utility Operations: count, exists, truncate
    
    TYPE SAFETY BENEFITS:
    ====================
    • Compile-time type checking
    • IDE autocomplete support
    • Method signature validation
    • Return type guarantee
    """
    
    def __init__(self, model: type[ModelType]):
        """
        BaseCRUD instance oluşturur
        
        ALGORITHM:
        1. Model class reference'ı store et
        2. Model name'i debugging için extract et
        3. Type safety validation (runtime'da implicit)
        
        Args:
            model (type[ModelType]): SQLAlchemy model class
            
        Example:
            >>> workflow_crud = BaseCRUD(Workflow)
            >>> node_crud = BaseCRUD(Node)
        """
        self.model = model                    # SQLAlchemy model class
        self.model_name = model.__name__      # Class name for error messages

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