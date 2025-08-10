from typing import Dict, List, Any, Optional

from .base_service import BaseService
from ..schemas.v1.env_var_schemas import EnvVarSummary


class EnvVarService(BaseService):
    """Environment Variable CRUD ve business logic işlemlerini yöneten servis"""

# ===================================================================================================  ENV VAR CREATE  ==
    async def env_var_create(self, env_var_data: Dict[str, Any]) -> Dict[str, Any]:
        """Yeni environment variable oluştur"""
        try:
            # DatabaseOrchestration session ile çağır
            with self.core.db_engine.get_session_context() as session:
                result = self.orchestrator.create_env_var(session, env_var_data)
                session.commit()
                result["message"] = "Environment variable operation completed successfully"
                return result
        except Exception as e:
            raise e

# ===================================================================================================  ENV VAR UPDATE  ==
    async def env_var_update(self, env_var_id: str, env_var_data: Dict[str, Any]) -> Dict[str, Any]:
        """Environment variable'ı güncelle"""
        try:
            with self.core.db_engine.get_session_context() as session:
                result = self.orchestrator.update_env_var(session, env_var_id, env_var_data)
                session.commit()
                result["message"] = "Environment variable operation completed successfully"
                return result
        except Exception as e:
            raise e

# ===================================================================================================  ENV VAR DELETE  ==
    async def env_var_delete(self, env_var_id: str) -> Dict[str, Any]:
        """Environment variable'ı sil"""
        try:
            with self.core.db_engine.get_session_context() as session:
                result = self.orchestrator.delete_env_var(session, env_var_id)
                session.commit()
                result["message"] = "Environment variable operation completed successfully"
                return result
        except Exception as e:
            raise e

# =================================================================================================  ENV VAR VALIDATE  ==
    async def env_var_validate(self, env_var_id: str) -> Dict[str, Any]:
        """Environment variable'ı doğrula"""
        try:
            with self.core.db_engine.get_session_context() as session:
                result = self.orchestrator.validate_env_var(session, env_var_id)
                result["message"] = "Environment variable operation completed successfully"
                return result
        except Exception as e:
            raise e

# ===================================================================================================  ENV VAR SEARCH  ==
    async def env_var_search(self, search_criteria: Dict[str, Any]) -> Dict[str, Any]:
        """Environment variable'ları filtrele/ara"""
        try:
            with self.core.db_engine.get_session_context() as session:
                result = self.orchestrator.search_env_vars(session, search_criteria)
                
                # Convert data to EnvVarSummary objects
                if 'data' in result:
                    result['data'] = [EnvVarSummary(**env_var_dict) for env_var_dict in result['data']]
                
                result["message"] = "Environment variable operation completed successfully"
                return result
        except Exception as e:
            raise e

# =====================================================================================================  ENV VAR LIST  ==
    async def env_var_list(self, include_all: bool = True, page: Optional[int] = None, page_size: Optional[int] = None) -> Dict[str, Any]:
        """Tüm environment variable'ları listele"""
        try:
            with self.core.db_engine.get_session_context() as session:
                result = self.orchestrator.get_env_vars(session, include_all, page, page_size)
                
                # Convert data to EnvVarSummary objects
                if 'data' in result:
                    result['data'] = [EnvVarSummary(**env_var_dict) for env_var_dict in result['data']]
                
                result["message"] = "Environment variable operation completed successfully"
                return result
        except Exception as e:
            raise e

# ======================================================================================================  ENV VAR GET  ==
    async def env_var_get(self, env_var_id: str, include_value: bool = False) -> Dict[str, Any]:
        """Environment variable detaylarını getir"""
        try:
            with self.core.db_engine.get_session_context() as session:
                result = self.orchestrator.get_env_var(session, env_var_id, include_value)
                
                # Convert data to EnvVarSummary object
                if 'data' in result:
                    result['data'] = EnvVarSummary(**result['data'])
                
                result["message"] = "Environment variable operation completed successfully"
                return result
        except Exception as e:
            raise e

# ====================================================================================================  ENV VAR COUNT  ==
    async def env_var_count(self, include_all: Optional[bool] = None) -> Dict[str, Any]:
        """Environment variable sayılarını getir"""
        try:
            with self.core.db_engine.get_session_context() as session:
                result = self.orchestrator.count_env_vars(session, include_all)
                result["message"] = "Environment variable operation completed successfully"
                return result
        except Exception as e:
            raise e

# ===================================================================================================  ENV VAR EXISTS  ==
    async def env_var_exists(self, env_var_id: str) -> Dict[str, Any]:
        """Environment variable'ın var olup olmadığını kontrol et"""
        try:
            with self.core.db_engine.get_session_context() as session:
                result = self.orchestrator.env_var_exists(session, env_var_id)
                result["message"] = "Environment variable operation completed successfully"
                return result
        except Exception as e:
            raise e

# =================================================================================================  ENV VAR DELETE ALL  ==
    async def env_var_delete_all(self) -> Dict[str, Any]:
        """Tüm environment variable'ları sil (tehlikeli operasyon)"""
        try:
            with self.core.db_engine.get_session_context() as session:
                result = self.orchestrator.delete_all_env_vars(session)
                session.commit()
                result["message"] = "Environment variable operation completed successfully"
                return result
        except Exception as e:
            raise e