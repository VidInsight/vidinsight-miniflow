from typing import Dict, Any, Optional

from .base_service import BaseService
from ..schemas.v1.edge_schemas import EdgeSummary


class EdgeService(BaseService):
    """Edge CRUD ve business logic işlemlerini yöneten servis"""

# =====================================================================================================  EDGE CREATE  ==
    async def edge_create(self, edge_data: Dict[str, Any]) -> Dict[str, Any]:
        """Yeni edge oluştur"""
        try:
            # DatabaseOrchestration session ile çağır
            with self.core.db_engine.get_session_context() as session:
                result = self.orchestrator.create_edge(session, edge_data)
                session.commit()
                result["message"] = "Edge created successfully"
                return result
        except Exception as e:
            raise e

# =====================================================================================================  EDGE UPDATE  ==
    async def edge_update(self, edge_id: str, edge_data: Dict[str, Any]) -> Dict[str, Any]:
        """Edge'i güncelle"""
        try:
            with self.core.db_engine.get_session_context() as session:
                result = self.orchestrator.update_edge(session, edge_id, edge_data)
                session.commit()
                result["message"] = "Edge operation completed successfully"
                return result
        except Exception as e:
            raise e

# =====================================================================================================  EDGE DELETE  ==
    async def edge_delete(self, edge_id: str) -> Dict[str, Any]:
        """Edge'i sil"""
        try:
            with self.core.db_engine.get_session_context() as session:
                result = self.orchestrator.delete_edge(session, edge_id)
                session.commit()
                result["message"] = "Edge operation completed successfully"
                return result
        except Exception as e:
            raise e

# ===================================================================================================  EDGE VALIDATE  ==
    async def edge_validate(self, edge_id: str) -> Dict[str, Any]:
        """Edge'i doğrula"""
        try:
            with self.core.db_engine.get_session_context() as session:
                result = self.orchestrator.validate_edge(session, edge_id)
                result["message"] = "Edge operation completed successfully"
                return result
        except Exception as e:
            raise e

# =====================================================================================================  EDGE SEARCH  ==
    async def edge_search(self, search_criteria: Dict[str, Any]) -> Dict[str, Any]:
        """Edge'leri filtrele/ara"""
        try:
            with self.core.db_engine.get_session_context() as session:
                result = self.orchestrator.search_edges(session, search_criteria)
                
                # Convert data to EdgeSummary objects
                if 'data' in result:
                    result['data'] = [EdgeSummary(**edge_dict) for edge_dict in result['data']]
                
                result["message"] = "Edge operation completed successfully"
                return result
        except Exception as e:
            raise e

# =======================================================================================================  EDGE LIST  ==
    async def edge_list(self, workflow_id: Optional[str] = None, page: Optional[int] = None, page_size: Optional[int] = None) -> Dict[str, Any]:
        """Tüm edge'leri listele veya belirli bir workflow'un edge'lerini listele"""
        try:
            with self.core.db_engine.get_session_context() as session:
                result = self.orchestrator.get_edges(session, workflow_id, page, page_size)
                
                # Convert data to EdgeSummary objects
                if 'data' in result:
                    result['data'] = [EdgeSummary(**edge_dict) for edge_dict in result['data']]
                
                result["message"] = "Edge operation completed successfully"
                return result
        except Exception as e:
            raise e

# ========================================================================================================  EDGE GET  ==
    async def edge_get(self, edge_id: str) -> Dict[str, Any]:
        """Edge detaylarını getir"""
        try:
            with self.core.db_engine.get_session_context() as session:
                result = self.orchestrator.get_edge(session, edge_id)
                
                # Convert data to EdgeSummary object
                if 'data' in result:
                    result['data'] = EdgeSummary(**result['data'])
                
                result["message"] = "Edge operation completed successfully"
                return result
        except Exception as e:
            raise e

# ======================================================================================================  EDGE COUNT  ==
    async def edge_count(self, workflow_id: Optional[str] = None) -> Dict[str, Any]:
        """Edge sayılarını getir (total, by workflow, etc.)"""
        try:
            with self.core.db_engine.get_session_context() as session:
                result = self.orchestrator.count_edges(session, workflow_id)
                result["message"] = "Edge operation completed successfully"
                return result
        except Exception as e:
            raise e

# =====================================================================================================  EDGE EXISTS  ==
    async def edge_exists(self, edge_id: str) -> Dict[str, Any]:
        """Edge'in var olup olmadığını kontrol et"""
        try:
            with self.core.db_engine.get_session_context() as session:
                result = self.orchestrator.edge_exists(session, edge_id)
                result["message"] = "Edge operation completed successfully"
                return result
        except Exception as e:
            raise e