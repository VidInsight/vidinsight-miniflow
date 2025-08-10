from typing import Dict, List, Any, Optional

from .base_service import BaseService
from ..schemas.v1.execution_schemas import ExecutionSummary


class ExecutionService(BaseService):
    """Execution CRUD ve business logic işlemlerini yöneten servis"""

# ===================================================================================================  EXECUTION CREATE  ==
    async def execution_create(self, execution_data: Dict[str, Any]) -> Dict[str, Any]:
        """Yeni execution oluştur"""
        try:
            with self.core.db_engine.get_session_context() as session:
                result = self.orchestrator.create_execution(session, execution_data)
                session.commit()
                result["message"] = "Execution operation completed successfully"
                return result
        except Exception as e:
            raise e

# ===================================================================================================  EXECUTION UPDATE  ==
    async def execution_update(self, execution_id: str, execution_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execution'ı güncelle"""
        try:
            with self.core.db_engine.get_session_context() as session:
                result = self.orchestrator.update_execution(session, execution_id, execution_data)
                session.commit()
                result["message"] = "Execution operation completed successfully"
                return result
        except Exception as e:
            raise e

# ===================================================================================================  EXECUTION DELETE  ==
    async def execution_delete(self, execution_id: str, force: bool = False) -> Dict[str, Any]:
        """Execution'ı sil"""
        try:
            with self.core.db_engine.get_session_context() as session:
                result = self.orchestrator.delete_execution(session, execution_id, force)
                session.commit()
                result["message"] = "Execution operation completed successfully"
                return result
        except Exception as e:
            raise e

# =================================================================================================  EXECUTION VALIDATE  ==
    async def execution_validate(self, execution_id: str) -> Dict[str, Any]:
        """Execution'ı doğrula"""
        try:
            with self.core.db_engine.get_session_context() as session:
                result = self.orchestrator.validate_execution(session, execution_id)
                result["message"] = "Execution operation completed successfully"
                return result
        except Exception as e:
            raise e

# ===================================================================================================  EXECUTION SEARCH  ==
    async def execution_search(self, search_criteria: Dict[str, Any]) -> Dict[str, Any]:
        """Execution'ları filtrele/ara"""
        try:
            with self.core.db_engine.get_session_context() as session:
                result = self.orchestrator.search_executions(session, search_criteria)
                
                # Convert data to ExecutionSummary objects
                if 'data' in result:
                    result['data'] = [ExecutionSummary(**execution_dict) for execution_dict in result['data']]
                
                result["message"] = "Execution operation completed successfully"
                return result
        except Exception as e:
            raise e

# =====================================================================================================  EXECUTION LIST  ==
    async def execution_list(self, workflow_id: Optional[str] = None, status: Optional[str] = None,
                           page: Optional[int] = None, page_size: Optional[int] = None) -> Dict[str, Any]:
        """Tüm execution'ları listele"""
        try:
            with self.core.db_engine.get_session_context() as session:
                result = self.orchestrator.get_executions_list(session, workflow_id, status, page, page_size)
                
                # Convert data to ExecutionSummary objects
                if 'data' in result:
                    result['data'] = [ExecutionSummary(**execution_dict) for execution_dict in result['data']]
                
                result["message"] = "Execution operation completed successfully"
                return result
        except Exception as e:
            raise e

# ======================================================================================================  EXECUTION GET  ==
    async def execution_get(self, execution_id: str, include_results: bool = False) -> Dict[str, Any]:
        """Execution detaylarını getir"""
        try:
            with self.core.db_engine.get_session_context() as session:
                result = self.orchestrator.get_execution_detail(session, execution_id, include_results)
                
                # Convert data to ExecutionSummary object
                if 'data' in result:
                    result['data'] = ExecutionSummary(**result['data'])
                
                result["message"] = "Execution operation completed successfully"
                return result
        except Exception as e:
            raise e

# ====================================================================================================  EXECUTION COUNT  ==
    async def execution_count(self, group_by: Optional[str] = None) -> Dict[str, Any]:
        """Execution sayılarını getir (total, by status, etc.)"""
        try:
            with self.core.db_engine.get_session_context() as session:
                result = self.orchestrator.count_executions(session, group_by)
                result["message"] = "Execution operation completed successfully"
                return result
        except Exception as e:
            raise e

# ===================================================================================================  EXECUTION EXISTS  ==
    async def execution_exists(self, execution_id: str) -> Dict[str, Any]:
        """Execution'ın var olup olmadığını kontrol et"""
        try:
            with self.core.db_engine.get_session_context() as session:
                result = self.orchestrator.execution_exists_check(session, execution_id)
                result["message"] = "Execution operation completed successfully"
                return result
        except Exception as e:
            raise e

# =================================================================================================  EXECUTION RESULTS  ==
    async def execution_results(self, execution_id: str) -> Dict[str, Any]:
        """Execution sonuçlarını getir"""
        try:
            with self.core.db_engine.get_session_context() as session:
                result = self.orchestrator.get_execution_results(session, execution_id)
                result["message"] = "Execution operation completed successfully"
                return result
        except Exception as e:
            raise e

# =================================================================================================  EXECUTION STATUS  ==
    async def execution_status(self, execution_id: str) -> Dict[str, Any]:
        """Execution durumunu getir"""
        try:
            with self.core.db_engine.get_session_context() as session:
                result = self.orchestrator.get_execution_status(session, execution_id)
                result["message"] = "Execution operation completed successfully"
                return result
        except Exception as e:
            raise e

# =================================================================================================  EXECUTION CANCEL  ==
    async def execution_cancel(self, execution_id: str, cancel_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execution'ı iptal et"""
        try:
            with self.core.db_engine.get_session_context() as session:
                result = self.orchestrator.cancel_execution_new(session, execution_id, cancel_data)
                session.commit()
                result["message"] = "Execution operation completed successfully"
                return result
        except Exception as e:
            raise e