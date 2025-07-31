from typing import List, Optional, Dict, Any
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import Session
from datetime import datetime

from .base_crud import BaseCRUD
from ..models import EnvironmentVariable


class EnvironmentVariableCRUD(BaseCRUD[EnvironmentVariable]):

    def __init__(self):
        super().__init__(EnvironmentVariable)

    """CRUD operations for EnvironmentVariable model. Inherits all standard CRUD methods from BaseCRUD."""

    # ENVIRONMENT VARIABLE ÖZEL YÖNETİMİ
    # ==============================================================
    def find_by_name(self, session: Session, name: str) -> Optional[EnvironmentVariable]:
        """Environment variable'ı isim ile bul"""
        stmt = select(self.model).where(self.model.name == name)
        return session.execute(stmt).scalar_one_or_none()

    def get_active_variables(self, session: Session) -> List[EnvironmentVariable]:
        """Aktif environment variable'ları getir"""
        stmt = select(self.model).where(self.model.is_active == True)
        return list(session.execute(stmt).scalars().all())

    def get_variable_value(self, session: Session, name: str) -> Optional[str]:
        """Environment variable'ın değerini getir (sadece aktif olanlar)"""
        stmt = select(self.model.value).where(
            and_(
                self.model.name == name,
                self.model.is_active == True
            )
        )
        return session.execute(stmt).scalar_one_or_none()

    def set_variable_value(self, session: Session, name: str, value: str) -> EnvironmentVariable:
        """Environment variable'ın değerini güncelle"""
        if not value:
            raise ValueError("Environment variable value cannot be empty")
        
        env_var = self.find_by_name(session, name)
        if not env_var:
            raise ValueError(f"Environment variable not found: {name}")
        
        env_var.value = value
        env_var.updated_at = datetime.utcnow()
        session.flush()
        
        return env_var

    def activate_variable(self, session: Session, name: str) -> EnvironmentVariable:
        """Environment variable'ı aktif hale getir"""
        env_var = self.find_by_name(session, name)
        if not env_var:
            raise ValueError(f"Environment variable not found: {name}")
        
        env_var.is_active = True
        env_var.updated_at = datetime.utcnow()
        session.flush()
        
        return env_var

    def deactivate_variable(self, session: Session, name: str) -> EnvironmentVariable:
        """Environment variable'ı deaktif hale getir"""
        env_var = self.find_by_name(session, name)
        if not env_var:
            raise ValueError(f"Environment variable not found: {name}")
        
        env_var.is_active = False
        env_var.updated_at = datetime.utcnow()
        session.flush()
        
        return env_var

    # KONTROL YÖNETİMİ
    # ==============================================================
    def check_name_exists(self, session: Session, name: str) -> bool:
        """Environment variable name var mı kontrol et"""
        stmt = select(func.count(self.model.id)).where(self.model.name == name)
        count = session.execute(stmt).scalar_one()
        return count > 0

    def check_active_name_exists(self, session: Session, name: str) -> bool:
        """Aktif environment variable name var mı kontrol et"""
        stmt = select(func.count(self.model.id)).where(
            and_(
                self.model.name == name,
                self.model.is_active == True
            )
        )
        count = session.execute(stmt).scalar_one()
        return count > 0

    # TOPLU İŞLEMLER
    # ==============================================================
    def bulk_activate(self, session: Session, names: List[str]) -> int:
        """Birden fazla environment variable'ı aktif hale getir"""
        if not names:
            return 0
        
        count = 0
        for name in names:
            try:
                self.activate_variable(session, name)
                count += 1
            except ValueError:
                # Variable bulunamaz ise skip et
                continue
        
        return count

    def bulk_deactivate(self, session: Session, names: List[str]) -> int:
        """Birden fazla environment variable'ı deaktif hale getir"""
        if not names:
            return 0
        
        count = 0
        for name in names:
            try:
                self.deactivate_variable(session, name)
                count += 1
            except ValueError:
                # Variable bulunamaz ise skip et
                continue
        
        return count

    def get_variables_as_dict(self, session: Session, active_only: bool = True) -> Dict[str, str]:
        """Environment variable'ları dictionary olarak getir"""
        if active_only:
            stmt = select(self.model.name, self.model.value).where(self.model.is_active == True)
        else:
            stmt = select(self.model.name, self.model.value)
        
        results = session.execute(stmt).all()
        return {row.name: row.value for row in results} 