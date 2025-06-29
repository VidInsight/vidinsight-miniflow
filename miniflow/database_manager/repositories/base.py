from abc import ABC
from typing import List, Optional, Dict, Any, Type
from sqlalchemy.orm import Session
# TEMPORARY: Commenting out circular import
# from ..core.manager import get_database_manager


class BaseRepository(ABC):
    """Base repository with common CRUD operations"""
    
    def __init__(self, model_class: Type, manager=None):
        self.model_class = model_class
        # TEMPORARY: Accept manager as parameter instead of global function
        self.manager = manager
        if not self.manager:
            raise ValueError("Manager instance required (get_database_manager disabled due to circular imports)")
    
    def create(self, **kwargs) -> Any:
        """Create a new record"""
        with self.manager.get_session() as session:
            instance = self.model_class(**kwargs)
            session.add(instance)
            session.commit()
            session.refresh(instance)
            return instance
    
    def get_by_id(self, id: str) -> Optional[Any]:
        """Get record by ID"""
        with self.manager.get_session() as session:
            return session.query(self.model_class).filter(self.model_class.id == id).first()
    
    def get_all(self, limit: int = 100, offset: int = 0) -> List[Any]:
        """Get all records with pagination"""
        with self.manager.get_session() as session:
            return session.query(self.model_class).offset(offset).limit(limit).all()
    
    def update(self, id: str, **kwargs) -> Optional[Any]:
        """Update record by ID"""
        with self.manager.get_session() as session:
            instance = session.query(self.model_class).filter(self.model_class.id == id).first()
            if instance:
                for key, value in kwargs.items():
                    if hasattr(instance, key):
                        setattr(instance, key, value)
                session.commit()
                session.refresh(instance)
            return instance
    
    def delete(self, id: str) -> bool:
        """Delete record by ID"""
        with self.manager.get_session() as session:
            instance = session.query(self.model_class).filter(self.model_class.id == id).first()
            if instance:
                session.delete(instance)
                session.commit()
                return True
            return False
    
    def count(self) -> int:
        """Count total records"""
        with self.manager.get_session() as session:
            return session.query(self.model_class).count()
    
    def exists(self, id: str) -> bool:
        """Check if record exists"""
        with self.manager.get_session() as session:
            return session.query(self.model_class).filter(self.model_class.id == id).first() is not None 