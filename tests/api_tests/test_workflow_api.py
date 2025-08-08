"""
TEST WORKFLOW API
===============

Workflow API endpoint testleri - Yeni yapı için güncellenmiş
"""

import pytest
from fastapi.testclient import TestClient
from miniflow.api import app


class TestWorkflowAPI:
    """Workflow API testleri"""
    
    @pytest.fixture
    def client(self):
        """Test client fixture"""
        return TestClient(app)
    
    @pytest.mark.api
    def test_workflow_create_api(self, client):
        """Workflow oluşturma API testi"""
        workflow_data = {
            "name": "api_test_workflow",
            "description": "API test workflow",
            "nodes": [
                {
                    "name": "test_node",
                    "script_id": None,
                    "params": {},
                    "max_retries": 3,
                    "timeout_seconds": 300
                }
            ],
            "edges": []
        }
        
        response = client.post("/api/v1/workflows/", json=workflow_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["status"] is True
        assert "workflow_id" in data
        assert "created_at" in data
        assert "nodes" in data
        assert "edges" in data
        
    @pytest.mark.api
    def test_workflow_get_api(self, client):
        """Workflow get API testi"""
        # First create a workflow
        workflow_data = {
            "name": "api_get_test_workflow",
            "description": "API get test workflow",
            "nodes": [
                {
                    "name": "test_node",
                    "script_id": None,
                    "params": {},
                    "max_retries": 3,
                    "timeout_seconds": 300
                }
            ],
            "edges": []
        }
        
        create_response = client.post("/api/v1/workflows/", json=workflow_data)
        workflow_id = create_response.json()["workflow_id"]
        
        # Then get the workflow
        response = client.get(f"/api/v1/workflows/{workflow_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] is True
        assert data["workflow_id"] == workflow_id
        assert data["name"] == workflow_data["name"]
        
    @pytest.mark.api
    def test_workflow_list_api(self, client):
        """Workflow list API testi"""
        response = client.get("/api/v1/workflows/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] is True
        assert "workflows" in data
        assert isinstance(data["workflows"], list)
        
    @pytest.mark.api
    def test_workflow_update_api(self, client):
        """Workflow update API testi"""
        # First create a workflow
        workflow_data = {
            "name": "api_update_test_workflow",
            "description": "API update test workflow",
            "nodes": [
                {
                    "name": "test_node",
                    "script_id": None,
                    "params": {},
                    "max_retries": 3,
                    "timeout_seconds": 300
                }
            ],
            "edges": []
        }
        
        create_response = client.post("/api/v1/workflows/", json=workflow_data)
        workflow_id = create_response.json()["workflow_id"]
        
        # Update the workflow
        update_data = workflow_data.copy()
        update_data["description"] = "Updated description"
        
        response = client.put(f"/api/v1/workflows/{workflow_id}", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] is True
        assert data["workflow_id"] == workflow_id
        
    @pytest.mark.api
    def test_workflow_delete_api(self, client):
        """Workflow delete API testi"""
        # First create a workflow
        workflow_data = {
            "name": "api_delete_test_workflow",
            "description": "API delete test workflow",
            "nodes": [
                {
                    "name": "test_node",
                    "script_id": None,
                    "params": {},
                    "max_retries": 3,
                    "timeout_seconds": 300
                }
            ],
            "edges": []
        }
        
        create_response = client.post("/api/v1/workflows/", json=workflow_data)
        workflow_id = create_response.json()["workflow_id"]
        
        # Delete the workflow
        response = client.delete(f"/api/v1/workflows/{workflow_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] is True
        
    @pytest.mark.api
    def test_workflow_validation_error(self, client):
        """Workflow validation error testi"""
        # Invalid workflow data (missing required fields)
        invalid_workflow_data = {
            "description": "Invalid workflow without name"
        }
        
        response = client.post("/api/v1/workflows/", json=invalid_workflow_data)
        
        assert response.status_code == 422  # Validation error
        
    @pytest.mark.api
    def test_health_check_api(self, client):
        """Health check API testi"""
        response = client.get("/api/v1/health/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data 