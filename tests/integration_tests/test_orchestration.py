"""
TEST ORCHESTRATION INTEGRATION
============================

Database orchestration entegrasyon testleri.
"""

import pytest
from miniflow.database_manager import DatabaseOrchestration


class TestOrchestrationIntegration:
    """Orchestration entegrasyon testleri"""
    
    @pytest.mark.integration
    def test_orchestration_creation(self, miniflow_core):
        """Orchestration oluşturma testi"""
        orchestration = DatabaseOrchestration()
        
        assert orchestration is not None
        assert hasattr(orchestration, 'workflow_crud')
        assert hasattr(orchestration, 'script_crud')
        assert hasattr(orchestration, 'execution_crud')
        
    @pytest.mark.integration
    def test_workflow_creation_integration(self, miniflow_core, sample_workflow_data):
        """Workflow oluşturma entegrasyon testi"""
        result = miniflow_core.workflow_create(sample_workflow_data)
        
        assert result is not None
        assert "workflow_id" in result
        assert "created_at" in result
        assert "nodes" in result
        assert "edges" in result
        
    @pytest.mark.integration
    def test_script_creation_integration(self, miniflow_core, sample_script_data, sample_script_content):
        """Script oluşturma entegrasyon testi"""
        result = miniflow_core.script_create(sample_script_data, sample_script_content)
        
        assert result is not None
        assert "script_id" in result
        assert "created_at" in result
        assert result["name"] == sample_script_data["name"]
        
    @pytest.mark.integration
    def test_workflow_execution_integration(self, miniflow_core, sample_workflow_data):
        """Workflow execution entegrasyon testi"""
        # Create workflow
        workflow_result = miniflow_core.workflow_create(sample_workflow_data)
        workflow_id = workflow_result["workflow_id"]
        
        # Trigger workflow
        execution_result = miniflow_core.trigger_workflow(workflow_id)
        
        assert execution_result is not None
        assert "execution_id" in execution_result
        assert "status" in execution_result
        
    @pytest.mark.integration
    def test_workflow_lifecycle_integration(self, miniflow_core, sample_workflow_data):
        """Workflow yaşam döngüsü entegrasyon testi"""
        # Create workflow
        workflow_result = miniflow_core.workflow_create(sample_workflow_data)
        workflow_id = workflow_result["workflow_id"]
        
        # Get workflow
        workflow = miniflow_core.workflow_get(workflow_id)
        assert workflow["id"] == workflow_id
        
        # Update workflow
        update_data = sample_workflow_data.copy()
        update_data["description"] = "Updated description"
        update_result = miniflow_core.workflow_update(workflow_id, update_data)
        assert update_result["workflow_id"] == workflow_id
        
        # Delete workflow
        delete_result = miniflow_core.workflow_delete(workflow_id)
        assert delete_result is not None
