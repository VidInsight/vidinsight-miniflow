from typing import Dict, List, Any, Optional

from .base_service import BaseService
from ..schemas.v1.node_schemas import NodeSummary


class NodeService(BaseService):
    """Node CRUD ve business logic işlemlerini yöneten servis"""

# =====================================================================================================  NODE CREATE  ==
    async def node_create(self, node_data: Dict[str, Any]) -> Dict[str, Any]:
        """Yeni node oluştur"""
        try:
            # DatabaseOrchestration session ile çağır
            with self.core.db_engine.get_session_context() as session:
                result = self.orchestrator.create_node(session, node_data)
                session.commit()
                result["message"] = "Node created successfully"
                return result
        except Exception as e:
            raise e

# =====================================================================================================  NODE UPDATE  ==
    async def node_update(self, node_id: str, node_data: Dict[str, Any]) -> Dict[str, Any]:
        """Node'u güncelle"""
        try:
            with self.core.db_engine.get_session_context() as session:
                result = self.orchestrator.update_node(session, node_id, node_data)
                session.commit()
                result["message"] = "Node updated successfully"
                return result
        except Exception as e:
            raise e

# =====================================================================================================  NODE DELETE  ==
    async def node_delete(self, node_id: str, force: bool = False) -> Dict[str, Any]:
        """Node'u sil"""
        try:
            with self.core.db_engine.get_session_context() as session:
                result = self.orchestrator.delete_node(session, node_id, force)
                session.commit()
                result["message"] = "Node deleted successfully"
                return result
        except Exception as e:
            raise e

# ===================================================================================================  NODE VALIDATE  ==
    async def node_validate(self, node_id: str) -> Dict[str, Any]:
        """Node'u doğrula"""
        try:
            with self.core.db_engine.get_session_context() as session:
                result = self.orchestrator.validate_node(session, node_id)
                result["message"] = "Node validation completed"
                return result
        except Exception as e:
            raise e

# =====================================================================================================  NODE SEARCH  ==
    async def node_search(self, search_criteria: Dict[str, Any]) -> Dict[str, Any]:
        """Node'ları filtrele/ara"""
        try:
            with self.core.db_engine.get_session_context() as session:
                result = self.orchestrator.search_nodes(session, search_criteria)
                
                # Convert data to NodeSummary objects
                if 'data' in result:
                    result['data'] = [NodeSummary(**node_dict) for node_dict in result['data']]

                result["message"] = "Operation completed successfully"
                return result
        except Exception as e:
            raise e

# =======================================================================================================  NODE LIST  ==
    async def node_list(self, workflow_id: Optional[str] = None, page: Optional[int] = None, page_size: Optional[int] = None) -> Dict[str, Any]:
        """Tüm node'ları listele veya belirli bir workflow'un node'larını listele"""
        try:
            with self.core.db_engine.get_session_context() as session:
                result = self.orchestrator.get_nodes(session, workflow_id, page, page_size)
                
                # Convert data to NodeSummary objects
                if 'data' in result:
                    result['data'] = [NodeSummary(**node_dict) for node_dict in result['data']]

                result["message"] = "Operation completed successfully"
                return result
        except Exception as e:
            raise e

# ========================================================================================================  NODE GET  ==
    async def node_get(self, node_id: str) -> Dict[str, Any]:
        """Node detaylarını getir"""
        try:
            with self.core.db_engine.get_session_context() as session:
                result = self.orchestrator.get_node(session, node_id)
                
                # Convert data to NodeSummary object
                if 'data' in result:
                    result['data'] = NodeSummary(**result['data'])

                result["message"] = "Operation completed successfully"
                return result
        except Exception as e:
            raise e

# ======================================================================================================  NODE COUNT  ==
    async def node_count(self, workflow_id: Optional[str] = None) -> Dict[str, Any]:
        """Node sayılarını getir (total, by workflow, etc.)"""
        try:
            with self.core.db_engine.get_session_context() as session:
                result = self.orchestrator.count_nodes(session, workflow_id)

                result["message"] = "Operation completed successfully"
                return result
        except Exception as e:
            raise e

# =====================================================================================================  NODE EXISTS  ==
    async def node_exists(self, node_id: str) -> Dict[str, Any]:
        """Node'un var olup olmadığını kontrol et"""
        try:
            with self.core.db_engine.get_session_context() as session:
                result = self.orchestrator.node_exists(session, node_id)

                result["message"] = "Operation completed successfully"
                return result
        except Exception as e:
            raise e