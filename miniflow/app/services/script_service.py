from typing import Dict, List, Any, Optional

from .base_service import BaseService
from ..schemas.v1.script_schemas import ScriptSummary


class ScriptService(BaseService):
    """Script CRUD ve business logic işlemlerini yöneten servis"""

# =====================================================================================================  SCRIPT CREATE  ==
    async def script_create(self, script_data: Dict[str, Any]) -> Dict[str, Any]:
        """Yeni script oluştur"""
        try:
            with self.core.db_engine.get_session_context() as session:
                result = self.orchestrator.create_script(session, script_data)
                session.commit()
                result["message"] = "Script created successfully"
                return result
        except Exception as e:
            raise e

# =====================================================================================================  SCRIPT UPDATE  ==
    async def script_update(self, script_id: str, script_data: Dict[str, Any]) -> Dict[str, Any]:
        """Script'i güncelle"""
        try:
            with self.core.db_engine.get_session_context() as session:
                result = self.orchestrator.update_script(session, script_id, script_data)
                session.commit()
                result["message"] = "Script operation completed successfully"
                return result
        except Exception as e:
            raise e

# =====================================================================================================  SCRIPT DELETE  ==
    async def script_delete(self, script_id: str, force: bool = False) -> Dict[str, Any]:
        """Script'i sil"""
        try:
            with self.core.db_engine.get_session_context() as session:
                result = self.orchestrator.delete_script(session, script_id, force)
                session.commit()
                result["message"] = "Script operation completed successfully"
                return result
        except Exception as e:
            raise e

# ===================================================================================================  SCRIPT VALIDATE  ==
    async def script_validate(self, script_id: str) -> Dict[str, Any]:
        """Script'i doğrula"""
        try:
            with self.core.db_engine.get_session_context() as session:
                result = self.orchestrator.validate_script(session, script_id)
                result["message"] = "Script operation completed successfully"
                return result
        except Exception as e:
            raise e

# =====================================================================================================  SCRIPT SEARCH  ==
    async def script_search(self, search_criteria: Dict[str, Any]) -> Dict[str, Any]:
        """Script'leri filtrele/ara"""
        try:
            with self.core.db_engine.get_session_context() as session:
                result = self.orchestrator.search_scripts(session, search_criteria)
                
                # Convert data to ScriptSummary objects
                if 'data' in result:
                    result['data'] = [ScriptSummary(**script_dict) for script_dict in result['data']]
                
                result["message"] = "Script operation completed successfully"
                return result
        except Exception as e:
            raise e

# =======================================================================================================  SCRIPT LIST  ==
    async def script_list(self, language: Optional[str] = None, test_status: Optional[str] = None, 
                         page: Optional[int] = None, page_size: Optional[int] = None) -> Dict[str, Any]:
        """Tüm script'leri listele"""
        try:
            with self.core.db_engine.get_session_context() as session:
                result = self.orchestrator.get_scripts(session, language, test_status, page, page_size)
                
                # Convert data to ScriptSummary objects
                if 'data' in result:
                    result['data'] = [ScriptSummary(**script_dict) for script_dict in result['data']]
                
                result["message"] = "Script operation completed successfully"
                return result
        except Exception as e:
            raise e

# ========================================================================================================  SCRIPT GET  ==
    async def script_get(self, script_id: str, include_content: bool = False) -> Dict[str, Any]:
        """Script detaylarını getir"""
        try:
            with self.core.db_engine.get_session_context() as session:
                result = self.orchestrator.get_script(session, script_id, include_content)
                
                # Convert data to ScriptSummary object
                if 'data' in result:
                    result['data'] = ScriptSummary(**result['data'])
                
                result["message"] = "Script operation completed successfully"
                return result
        except Exception as e:
            raise e

# ======================================================================================================  SCRIPT COUNT  ==
    async def script_count(self, group_by: Optional[str] = None) -> Dict[str, Any]:
        """Script sayılarını getir (total, by language, etc.)"""
        try:
            with self.core.db_engine.get_session_context() as session:
                result = self.orchestrator.count_scripts(session, group_by)
                result["message"] = "Script operation completed successfully"
                return result
        except Exception as e:
            raise e

# =====================================================================================================  SCRIPT EXISTS  ==
    async def script_exists(self, script_id: str) -> Dict[str, Any]:
        """Script'in var olup olmadığını kontrol et"""
        try:
            with self.core.db_engine.get_session_context() as session:
                result = self.orchestrator.script_exists(session, script_id)
                result["message"] = "Script operation completed successfully"
                return result
        except Exception as e:
            raise e

# =====================================================================================================  SCRIPT TEST  ==
    async def script_test(self, script_id: str, test_data: Dict[str, Any]) -> Dict[str, Any]:
        """Script'i test et"""
        try:
            with self.core.db_engine.get_session_context() as session:
                result = self.orchestrator.test_script(session, script_id, test_data)
                session.commit()  # Commit test status update
                result["message"] = "Script operation completed successfully"
                return result
        except Exception as e:
            raise e