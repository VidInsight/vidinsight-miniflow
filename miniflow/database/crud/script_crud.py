from typing import List, Optional, Dict, Any
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import Session
from datetime import datetime

from .base_crud import BaseCRUD
from ..models import Script, ScriptType, TestStatus, Node


class ScriptCRUD(BaseCRUD[Script]):

    def __init__(self):
        super().__init__(Script)

    """
    BaseCRUD'dan miras alınan fonksiyonlar:
    ============================================================
    - create()
    - find_by_id()
    - find_by_name() 
    - update()
    - delete()
    - get_all()
    - count(), 
    - exists()
    - filter() 
    - order_by()
    - select_in_bulk()
    - truncate(),
    - bulk_create()
    - bulk_update()
    - bulk_delete()
    """

    # SCRIPT PATH YÖNETİMİ
    # ==============================================================
    def get_script_path(self, session: Session, script_id: str) -> Optional[str]:
        """Script'in dosya yolunu getir"""
        script = self.find_by_id(session, script_id)
        return script.script_path if script else None

    def set_script_path(self, session: Session, script_id: str, script_path: str) -> Script:
        """Script'in dosya yolunu güncelle"""
        if not script_path or not script_path.strip():
            raise ValueError("Script path cannot be empty")
        
        script = self.find_by_id(session, script_id)
        if not script:
            raise ValueError(f"Script not found: {script_id}")
        
        script.script_path = script_path.strip()
        script.updated_at = datetime.utcnow()
        session.flush()
        
        return script


    # TEST STATUS YÖNETİMİ
    # ==============================================================
    def get_test_status(self, session: Session, script_id: str) -> Optional[TestStatus]:
        """Script'in test durumunu getir"""
        script = self.find_by_id(session, script_id)
        return script.test_status if script else None

    def set_test_status(self, session: Session, script_id: str, test_status: TestStatus) -> Script:
        """Script'in test durumunu güncelle"""
        script = self.find_by_id(session, script_id)
        if not script:
            raise ValueError(f"Script not found: {script_id}")
        
        script.test_status = test_status
        script.updated_at = datetime.utcnow()
        session.flush()
        
        return script


    # SCRIPT SORGULAMA YÖNETİMİ
    # ==============================================================
    def get_scripts_by_language(self, session: Session, language: ScriptType) -> List[Script]:
        """Script diline göre script'leri getir"""
        stmt = select(self.model).where(self.model.language == language)
        return list(session.execute(stmt).scalars().all())

    def get_scripts_by_test_status(self, session: Session, test_status: TestStatus) -> List[Script]:
        """Test durumuna göre script'leri getir"""
        stmt = select(self.model).where(self.model.test_status == test_status)
        return list(session.execute(stmt).scalars().all())

    def get_scripts_used_by_node(self, session: Session, node_id: str) -> List[Script]:
        """Bir node tarafından kullanılan script'leri getir"""
        stmt = select(self.model).join(Node).where(Node.id == node_id)
        return list(session.execute(stmt).scalars().all())

    def get_scripts_by_workflow(self, session: Session, workflow_id: str) -> List[Script]:
        """Bir workflow'da kullanılan script'leri getir"""
        stmt = select(self.model).join(Node).where(Node.workflow_id == workflow_id)
        return list(session.execute(stmt).scalars().all())
    
    def check_script_exists(self, session: Session, script_id: str) -> bool:
        """Script ID var mı kontrol et - TEK GÖREV"""
        stmt = select(func.count(self.model.id)).where(self.model.id == script_id)
        count = session.execute(stmt).scalar_one()
        return count > 0
    
    def check_name_exists(self, session: Session, name: str) -> bool:
        """Script name var mı kontrol et - TEK GÖREV"""
        stmt = select(func.count(self.model.id)).where(self.model.name == name)
        count = session.execute(stmt).scalar_one()
        return count > 0

