from typing import Any, Dict, Generic, List, Optional, TypeVar, Union
from sqlalchemy import select, func, delete, update
from sqlalchemy.orm import DeclarativeMeta, Session


ModelType = TypeVar("ModelType", bound=DeclarativeMeta)


class BaseCRUD(Generic[ModelType]):
    def __init__(self, model: type[ModelType]):
        self.model = model
        self.model_name = model.__name__

    # TEMEL CRUD
    # ============================================================== 

    def create(self, session: Session, **model_data):
        """Yeni kayıt oluştur"""
        if not model_data:
            raise ValueError("No data given for insterting to database")

        db_object = self.model(**model_data)
        session.add(db_object)
        session.flush()
        
        return db_object
    
    def find_by_id(self, session: Session, record_id: Union[str, int]) -> Optional[ModelType]:
        """ID'ye göre kayıt getir"""
        result = session.get(self.model, record_id)
        if not result:
            raise ValueError(f"{self.model_name} not found: {record_id}")
        return result
    
    def find_by_name(self, session: Session, name: str) -> Optional[ModelType]:
        """Name'e göre kayıt getir"""
        if not hasattr(self.model, 'name'):
            raise ValueError(f"{self.model_name} does not have a 'name' field")
        
        stmt = select(self.model).where(self.model.name == name)
        result = session.execute(stmt).scalar_one_or_none()
        
        if not result:
            raise ValueError(f"{self.model_name} not found with name: {name}")
        return result
    
    def update(self, session: Session, record_id: Union[str, int], **model_data) -> ModelType:
        """Kayıt güncelle"""
        if not model_data:
            raise ValueError("No data given for insterting to database")
        
        db_object = self.find_by_id(session, record_id)
        
        for field, value in model_data.items():
            if hasattr(db_object, field):
                setattr(db_object, field, value)
        
        session.flush()
        return db_object

    def delete(self, session: Session, record_id: Union[str, int]) -> ModelType:
        """Kayıt sil"""
        db_object = self.find_by_id(session, record_id)
        session.delete(db_object)
        session.flush()
        
        return db_object

    # EKSTRA CRUD
    # ============================================================== 

    def get_all(self, session: Session, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """Tüm kayıtları getir"""
        stmt = select(self.model).offset(skip).limit(limit)
        return list(session.execute(stmt).scalars().all())

    def count(self, session: Session) -> int:
        """Kayıt sayısını getir"""
        stmt = select(func.count(self.model.id))
        return session.execute(stmt).scalar_one()

    def exists(self, session: Session, record_id: Union[str, int]) -> bool:
        """Kayıt var mı kontrol et"""
        stmt = select(func.count(self.model.id)).where(self.model.id == record_id)
        return session.execute(stmt).scalar_one() > 0

    def filter(self, session: Session, filters: Dict[str, Any], skip: int = 0, limit: int = 100) -> List[ModelType]:
        """Filtreleme ile kayıtları getir"""
        stmt = select(self.model)
        
        for field_name, field_value in filters.items():
            if hasattr(self.model, field_name):
                stmt = stmt.where(getattr(self.model, field_name) == field_value)
            else:
                raise ValueError(f"Field '{field_name}' does not exist in {self.model_name}")
        
        stmt = stmt.offset(skip).limit(limit)
        return list(session.execute(stmt).scalars().all())

    def order_by(self, session: Session, order_field: str, desc: bool = False, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """Sıralama ile kayıtları getir"""
        if not hasattr(self.model, order_field):
            raise ValueError(f"Field '{order_field}' does not exist in {self.model_name}")
        
        order_column = getattr(self.model, order_field)
        if desc:
            order_column = order_column.desc()
        
        stmt = select(self.model).order_by(order_column).offset(skip).limit(limit)
        return list(session.execute(stmt).scalars().all())
    
    # BULK CRUD
    # ============================================================== 

    def select_in_bulk(self, session: Session, ids: List[Union[str, int]]) -> List[ModelType]:
        """Çoklu ID ile kayıtları getir"""
        if not ids:
            return []
        
        stmt = select(self.model).where(self.model.id.in_(ids))
        return list(session.execute(stmt).scalars().all())
    
    def truncate(self, session: Session) -> int:
        """Tüm kayıtları sil ve sayıyı döndür"""
        # Önce sayıyı al
        count = self.count(session)
        
        # Tüm kayıtları sil
        stmt = delete(self.model)
        session.execute(stmt)
        session.flush()
        
        return count
    
    def bulk_create(self, session: Session, objects_data: List[Dict[str, Any]]) -> int:
        """Gerçek bulk create - tek SQL ile çoklu INSERT"""
        if not objects_data:
            return 0
        
        # SQLAlchemy bulk insert kullan
        session.bulk_insert_mappings(self.model, objects_data)
        session.flush()
        
        return len(objects_data)
    
    def bulk_update(self, session: Session, updates: List[Dict[str, Any]]) -> int:
        """Gerçek bulk update - tek SQL ile çoklu UPDATE"""
        if not updates:
            return 0
        
        # ID'leri kontrol et
        for update_data in updates:
            if 'id' not in update_data:
                raise ValueError("'id' field is required for bulk update")
        
        # SQLAlchemy bulk update kullan
        session.bulk_update_mappings(self.model, updates)
        session.flush()
        
        return len(updates)
    
    def bulk_delete(self, session: Session, ids: List[Union[str, int]]) -> int:
        """Gerçek bulk delete - tek SQL ile çoklu DELETE"""
        if not ids:
            return 0
        
        # SQLAlchemy bulk delete kullan
        stmt = delete(self.model).where(self.model.id.in_(ids))
        result = session.execute(stmt)
        session.flush()
        
        deleted_count = result.rowcount or 0
        return deleted_count