from typing import Dict, List, Any, Optional

from .base_service import BaseService
from ..schemas.v1 import WorkflowSummary, WorkflowDetail


class WorkflowService(BaseService):
    """Workflow CRUD ve business logic işlemlerini yöneten servis"""

# =================================================================================================  WORKFLOW CREATE  ==
    async def workflow_create(self, workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        """Yeni workflow oluştur"""
        try:
            with self.core.db_engine.get_session_context() as session:
                result = self.orchestrator.create_workflow(session, workflow_data)
                session.commit()
                result["message"] = "Workflow created successfully"
                return result
        except Exception as e:
            raise e

# =================================================================================================  WORKFLOW UPDATE  ==
    async def workflow_update(self, workflow_id: str, workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        """Workflow'u güncelle"""
        try:
            with self.core.db_engine.get_session_context() as session:
                result = self.orchestrator.update_workflow(session, workflow_id, workflow_data)
                session.commit()
                result["message"] = "Workflow updated successfully"
                return result
        except Exception as e:
            raise e

# =================================================================================================  WORKFLOW DELETE  ==
    async def workflow_delete(self, workflow_id: str, force: bool = False) -> Dict[str, Any]:
        """Workflow'u sil"""
        try:
            with self.core.db_engine.get_session_context() as session:
                result = self.orchestrator.delete_workflow(session, workflow_id, force)
                session.commit()
                result["message"] = "Workflow deleted successfully"
                return result
        except Exception as e:
            raise e

# ===============================================================================================  WORKFLOW VALIDATE  ==
    async def workflow_validate(self, workflow_id: str) -> Dict[str, Any]:
        """Workflow doğrula"""
        try:
            with self.core.db_engine.get_session_context() as session:
                result = self.orchestrator.validate_workflow(session, workflow_id)
                result["message"] = "Workflow validation completed"
                return result
        except Exception as e:
            raise e

# =================================================================================================  WORKFLOW SEARCH  ==
    async def workflow_search(self, search_criteria: Dict[str, Any]) -> Dict[str, Any]:
        """Workflow'ları filtrele/ara"""
        try:
            with self.core.db_engine.get_session_context() as session:
                result = self.orchestrator.search_workflows(session, search_criteria)
                
                # Convert to schema-compatible format
                workflow_summaries = []
                for workflow_data in result['data']:
                    workflow_summaries.append(WorkflowSummary(**workflow_data))
                
                return {
                    "message": result['message'],
                    "data": workflow_summaries,
                    "total_count": result['total_count']
                }
        except Exception as e:
            raise e

# ====================================================================================================  WORKFLOW RUN  ==
    async def workflow_run(self, workflow_id: str) -> Dict[str, Any]:
        """Workflow'u çalıştır"""
        try:
            with self.core.db_engine.get_session_context() as session:
                result = self.orchestrator.run_workflow(session, workflow_id)
                session.commit()
                result["message"] = "Workflow execution started successfully"
                return result
        except Exception as e:
            raise e

# ==================================================================================================  WORKFLOW CLONE  ==
    async def workflow_clone(self, workflow_id: str, clone_data: Dict[str, Any]) -> Dict[str, Any]:
        """Workflow'u klonla"""
        try:
            with self.core.db_engine.get_session_context() as session:
                result = self.orchestrator.clone_workflow(session, workflow_id, clone_data)
                session.commit()
                result["message"] = "Workflow cloned successfully"
                return result
        except Exception as e:
            raise e

# ===================================================================================================  WORKFLOW LIST  ==
    async def workflow_list(self, status: Optional[str] = None, is_active: Optional[bool] = None,
                           page: Optional[int] = None, page_size: Optional[int] = None) -> Dict[str, Any]:
        """Tüm workflow'ları listele"""
        try:
            with self.core.db_engine.get_session_context() as session:
                result = self.orchestrator.get_workflows(session, status=status, is_active=is_active,
                                                        page=page, page_size=page_size)
                
                # Convert to schema-compatible format
                workflow_summaries = []
                for workflow_data in result['data']:
                    workflow_summaries.append(WorkflowSummary(**workflow_data))
                
                return {
                    "message": result['message'],
                    "data": workflow_summaries,
                    "total_count": result['total_count']
                }
        except Exception as e:
            raise e

# ====================================================================================================  WORKFLOW GET  ==
    async def workflow_get(self, workflow_id: str, include_nodes: bool = False, 
                          include_edges: bool = False) -> Dict[str, Any]:
        """Workflow detaylarını getir"""
        try:
            with self.core.db_engine.get_session_context() as session:
                result = self.orchestrator.get_workflow(session, workflow_id, 
                                                       include_nodes=include_nodes, include_edges=include_edges)
                
                # Convert to schema-compatible format
                workflow_detail = WorkflowDetail(**result['data'])
                
                return {
                    "message": result['message'],
                    "data": workflow_detail
                }
        except Exception as e:
            raise e

# ==================================================================================================  WORKFLOW COUNT  ==
    async def workflow_count(self, group_by: Optional[str] = None) -> Dict[str, Any]:
        """Workflow sayılarını getir (total, active, inactive)"""
        try:
            with self.core.db_engine.get_session_context() as session:
                result = self.orchestrator.count_workflows(session, group_by=group_by)
                result["message"] = "Workflow count retrieved successfully"
                return result
        except Exception as e:
            raise e

# =================================================================================================  WORKFLOW EXISTS  ==
    async def workflow_exists(self, workflow_id: str) -> Dict[str, Any]:
        """Workflow'un var olup olmadığını kontrol et"""
        try:
            with self.core.db_engine.get_session_context() as session:
                result = self.orchestrator.workflow_exists(session, workflow_id)
                result["message"] = "Workflow existence check completed"
                return result
        except Exception as e:
            raise e