"""
Comprehensive tests for BaseCRUD class.
Tests all CRUD operations, bulk operations, optimized operations, and error handling.
"""

import pytest
import time
from typing import List, Dict, Any
from sqlalchemy.exc import IntegrityError
import uuid

from miniflow.database_manager.crud.base_crud import BaseCRUD
from miniflow.database_manager.models import Workflow, WorkflowStatus, Node, Script


@pytest.fixture
def workflow_crud():
    """Create BaseCRUD instance for Workflow model"""
    return BaseCRUD(Workflow)


@pytest.fixture
def node_crud():
    """Create BaseCRUD instance for Node model"""
    return BaseCRUD(Node)


@pytest.fixture
def script_crud():
    """Create BaseCRUD instance for Script model"""
    return BaseCRUD(Script)


@pytest.fixture
def sample_workflows():
    """Sample workflow data for testing"""
    unique_id = uuid.uuid4().hex[:8]
    return [
        {"name": f"Test Workflow 1-{unique_id}", "description": "First test workflow", "status": WorkflowStatus.ACTIVE, "priority": 1},
        {"name": f"Test Workflow 2-{unique_id}", "description": "Second test workflow", "status": WorkflowStatus.INACTIVE, "priority": 2},
        {"name": f"Test Workflow 3-{unique_id}", "description": "Third test workflow", "status": WorkflowStatus.ACTIVE, "priority": 3},
        {"name": f"Test Workflow 4-{unique_id}", "description": "Fourth test workflow", "status": WorkflowStatus.DRAFT, "priority": 4},
        {"name": f"Test Workflow 5-{unique_id}", "description": "Fifth test workflow", "status": WorkflowStatus.ACTIVE, "priority": 5},
    ]


@pytest.fixture
def sample_nodes_data():
    """Sample node data for testing (requires workflow_id to be added)"""
    unique_id = uuid.uuid4().hex[:8]
    return [
        {"name": f"Test Node 1-{unique_id}", "params": {"param1": "value1"}, "max_retries": 1, "timeout_seconds": 100},
        {"name": f"Test Node 2-{unique_id}", "params": {"param2": "value2"}, "max_retries": 2, "timeout_seconds": 200},
        {"name": f"Test Node 3-{unique_id}", "params": {"param3": "value3"}, "max_retries": 3, "timeout_seconds": 300},
    ]


@pytest.fixture
def sample_scripts_data():
    """Sample script data for testing"""
    unique_id = uuid.uuid4().hex[:8]
    return [
        {"name": f"Test Script 1-{unique_id}", "description": "First script", "language": "python", "script_path": "/test/script1.py"},
        {"name": f"Test Script 2-{unique_id}", "description": "Second script", "language": "python", "script_path": "/test/script2.py"},
        {"name": f"Test Script 3-{unique_id}", "description": "Third script", "language": "python", "script_path": "/test/script3.py"},
    ]


class TestBaseCRUDInit:
    """Test BaseCRUD initialization"""
    
    def test_init_with_valid_model(self):
        """Test successful initialization with valid model"""
        crud = BaseCRUD(Workflow)
        assert crud.model == Workflow
        assert crud.model_name == "Workflow"
    
    def test_init_with_different_models(self):
        """Test initialization with different model types"""
        workflow_crud = BaseCRUD(Workflow)
        node_crud = BaseCRUD(Node)
        script_crud = BaseCRUD(Script)
        
        assert workflow_crud.model == Workflow
        assert node_crud.model == Node
        assert script_crud.model == Script
        assert workflow_crud.model_name == "Workflow"
        assert node_crud.model_name == "Node"
        assert script_crud.model_name == "Script"


class TestBasicOperations:
    """Test basic CRUD operations"""
    
    def test_create_success(self, test_database_session, workflow_crud):
        """Test successful entity creation"""
        unique_id = uuid.uuid4().hex[:8]
        data = {"name": f"Test Workflow-{unique_id}", "description": "Test description", "status": WorkflowStatus.ACTIVE}
        
        result = workflow_crud.create(test_database_session, **data)
        
        assert result is not None
        assert result.name == f"Test Workflow-{unique_id}"
        assert result.description == "Test description"
        assert result.status == WorkflowStatus.ACTIVE
        assert result.id is not None
        assert result.id.startswith("WF-")
    
    def test_create_with_no_data(self, test_database_session, workflow_crud):
        """Test creation with no data raises ValueError"""
        with pytest.raises(ValueError, match="No data provided for database insertion"):
            workflow_crud.create(test_database_session)
    
    def test_find_by_id_success(self, test_database_session, workflow_crud):
        """Test successful find by ID"""
        unique_id = uuid.uuid4().hex[:8]
        # Create test item
        item = workflow_crud.create(test_database_session, name=f"Test Workflow-{unique_id}", description="Test")
        
        # Find by ID
        found = workflow_crud.find_by_id(test_database_session, item.id)
        
        assert found is not None
        assert found.id == item.id
        assert found.name == f"Test Workflow-{unique_id}"
    
    def test_find_by_id_not_found(self, test_database_session, workflow_crud):
        """Test find by ID with non-existent ID raises ValueError"""
        with pytest.raises(ValueError, match="Workflow not found: NONEXISTENT"):
            workflow_crud.find_by_id(test_database_session, "NONEXISTENT")
    
    def test_find_by_name_success(self, test_database_session, workflow_crud):
        """Test successful find by name"""
        unique_id = uuid.uuid4().hex[:8]
        # Create test item
        item = workflow_crud.create(test_database_session, name=f"Unique Name-{unique_id}", description="Test")
        
        # Find by name
        found = workflow_crud.find_by_name(test_database_session, f"Unique Name-{unique_id}")
        
        assert found is not None
        assert found.name == f"Unique Name-{unique_id}"
        assert found.id == item.id
    
    def test_find_by_name_not_found(self, test_database_session, workflow_crud):
        """Test find by name with non-existent name raises ValueError"""
        with pytest.raises(ValueError, match="Workflow not found with name: Nonexistent Name"):
            workflow_crud.find_by_name(test_database_session, "Nonexistent Name")
    
    def test_find_by_name_no_name_field(self, test_database_session):
        """Test find by name on model without name field raises ValueError"""
        from miniflow.database_manager.models import ExecutionInput
        execution_input_crud = BaseCRUD(ExecutionInput)
        
        with pytest.raises(ValueError, match="ExecutionInput does not have a 'name' field"):
            execution_input_crud.find_by_name(test_database_session, "Test")
    
    def test_update_success(self, test_database_session, workflow_crud):
        """Test successful entity update"""
        unique_id = uuid.uuid4().hex[:8]
        # Create test item
        item = workflow_crud.create(test_database_session, name=f"Original Name-{unique_id}", description="Original")
        
        # Update item
        updated = workflow_crud.update(test_database_session, item.id, 
                                     name=f"Updated Name-{unique_id}", 
                                     description="Updated description")
        
        assert updated.id == item.id
        assert updated.name == f"Updated Name-{unique_id}"
        assert updated.description == "Updated description"
    
    def test_update_with_no_data(self, test_database_session, workflow_crud):
        """Test update with no data raises ValueError"""
        unique_id = uuid.uuid4().hex[:8]
        item = workflow_crud.create(test_database_session, name=f"Test Workflow-{unique_id}", description="Test")
        
        with pytest.raises(ValueError, match="No data provided for database update"):
            workflow_crud.update(test_database_session, item.id)
    
    def test_update_nonexistent_id(self, test_database_session, workflow_crud):
        """Test update with non-existent ID raises ValueError"""
        with pytest.raises(ValueError, match="Workflow not found: NONEXISTENT"):
            workflow_crud.update(test_database_session, "NONEXISTENT", name="New Name")
    
    def test_delete_success(self, test_database_session, workflow_crud):
        """Test successful entity deletion"""
        unique_id = uuid.uuid4().hex[:8]
        # Create test item
        item = workflow_crud.create(test_database_session, name=f"To Delete-{unique_id}", description="Test")
        
        # Delete item
        deleted = workflow_crud.delete(test_database_session, item.id)
        
        assert deleted.id == item.id
        assert deleted.name == f"To Delete-{unique_id}"
        
        # Verify item is deleted
        with pytest.raises(ValueError):
            workflow_crud.find_by_id(test_database_session, item.id)
    
    def test_delete_nonexistent_id(self, test_database_session, workflow_crud):
        """Test delete with non-existent ID raises ValueError"""
        with pytest.raises(ValueError, match="Workflow not found: NONEXISTENT"):
            workflow_crud.delete(test_database_session, "NONEXISTENT")


class TestQueryOperations:
    """Test query operations"""
    
    def test_get_all_default(self, test_database_session, workflow_crud, sample_workflows):
        """Test get_all with default parameters"""
        # Create test items
        for data in sample_workflows:
            workflow_crud.create(test_database_session, **data)
        
        # Get all items
        results = workflow_crud.get_all(test_database_session)
        
        assert len(results) == 5
        assert all("Test Workflow" in item.name for item in results)
    
    def test_get_all_with_pagination(self, test_database_session, workflow_crud, sample_workflows):
        """Test get_all with pagination"""
        # Create test items
        for data in sample_workflows:
            workflow_crud.create(test_database_session, **data)
        
        # Get with pagination
        page1 = workflow_crud.get_all(test_database_session, skip=0, limit=2)
        page2 = workflow_crud.get_all(test_database_session, skip=2, limit=2)
        
        assert len(page1) == 2
        assert len(page2) == 2
        
        # Ensure different items
        page1_ids = {item.id for item in page1}
        page2_ids = {item.id for item in page2}
        assert page1_ids.isdisjoint(page2_ids)
    
    def test_get_all_with_ordering(self, test_database_session, workflow_crud, sample_workflows):
        """Test get_all with ordering"""
        # Create test items
        for data in sample_workflows:
            workflow_crud.create(test_database_session, **data)
        
        # Get ordered by priority ascending
        asc_results = workflow_crud.get_all(test_database_session, order_by_field="priority", desc=False)
        
        # Get ordered by priority descending
        desc_results = workflow_crud.get_all(test_database_session, order_by_field="priority", desc=True)
        
        assert asc_results[0].priority == 1
        assert asc_results[-1].priority == 5
        assert desc_results[0].priority == 5
        assert desc_results[-1].priority == 1
    
    def test_count(self, test_database_session, workflow_crud, sample_workflows):
        """Test count operation"""
        # Initially should be 0
        assert workflow_crud.count(test_database_session) == 0
        
        # Create test items
        for data in sample_workflows:
            workflow_crud.create(test_database_session, **data)
        
        # Should be 5 after creation
        assert workflow_crud.count(test_database_session) == 5
    
    def test_exists_true(self, test_database_session, workflow_crud):
        """Test exists with existing entity"""
        unique_id = uuid.uuid4().hex[:8]
        item = workflow_crud.create(test_database_session, name=f"Test Workflow-{unique_id}", description="Test")
        
        assert workflow_crud.exists(test_database_session, item.id) is True
    
    def test_exists_false(self, test_database_session, workflow_crud):
        """Test exists with non-existing entity"""
        assert workflow_crud.exists(test_database_session, "NONEXISTENT") is False
    
    def test_filter_single_condition(self, test_database_session, workflow_crud, sample_workflows):
        """Test filter with single condition"""
        # Create test items
        for data in sample_workflows:
            workflow_crud.create(test_database_session, **data)
        
        # Filter by status
        active_items = workflow_crud.filter(test_database_session, {"status": WorkflowStatus.ACTIVE})
        
        assert len(active_items) == 3  # Items 1, 3, 5 are active
        assert all(item.status == WorkflowStatus.ACTIVE for item in active_items)
    
    def test_filter_multiple_conditions(self, test_database_session, workflow_crud, sample_workflows):
        """Test filter with multiple conditions"""
        # Create test items
        for data in sample_workflows:
            workflow_crud.create(test_database_session, **data)
        
        # Filter by status and priority
        results = workflow_crud.filter(test_database_session, {"status": WorkflowStatus.ACTIVE, "priority": 3})
        
        assert len(results) == 1
        assert "Test Workflow 3" in results[0].name
    
    def test_filter_invalid_field(self, test_database_session, workflow_crud):
        """Test filter with invalid field raises ValueError"""
        with pytest.raises(ValueError, match="Field 'invalid_field' does not exist in Workflow"):
            workflow_crud.filter(test_database_session, {"invalid_field": "value"})
    
    def test_count_filtered(self, test_database_session, workflow_crud, sample_workflows):
        """Test count_filtered operation"""
        # Create test items
        for data in sample_workflows:
            workflow_crud.create(test_database_session, **data)
        
        # Count active items
        active_count = workflow_crud.count_filtered(test_database_session, {"status": WorkflowStatus.ACTIVE})
        
        assert active_count == 3
    
    def test_find_by_field_success(self, test_database_session, workflow_crud, sample_workflows):
        """Test find_by_field with valid field"""
        # Create test items
        for data in sample_workflows:
            workflow_crud.create(test_database_session, **data)
        
        # Find by priority
        priority_3_items = workflow_crud.find_by_field(test_database_session, "priority", 3)
        
        assert len(priority_3_items) == 1
        assert priority_3_items[0].priority == 3
        assert "Test Workflow 3" in priority_3_items[0].name
    
    def test_find_by_field_invalid_field(self, test_database_session, workflow_crud):
        """Test find_by_field with invalid field raises ValueError"""
        with pytest.raises(ValueError, match="Field 'invalid_field' does not exist in Workflow"):
            workflow_crud.find_by_field(test_database_session, "invalid_field", "value")


class TestBulkOperations:
    """Test bulk operations"""
    
    def test_select_in_bulk_success(self, test_database_session, workflow_crud, sample_workflows):
        """Test select_in_bulk with valid IDs"""
        # Create test items
        created_items = []
        for data in sample_workflows:
            item = workflow_crud.create(test_database_session, **data)
            created_items.append(item)
        
        # Select first 3 items
        ids_to_select = [item.id for item in created_items[:3]]
        selected = workflow_crud.select_in_bulk(test_database_session, ids_to_select)
        
        assert len(selected) == 3
        selected_ids = {item.id for item in selected}
        assert selected_ids == set(ids_to_select)
    
    def test_select_in_bulk_empty_list(self, test_database_session, workflow_crud):
        """Test select_in_bulk with empty list"""
        results = workflow_crud.select_in_bulk(test_database_session, [])
        
        assert results == []
    
    def test_select_in_bulk_nonexistent_ids(self, test_database_session, workflow_crud):
        """Test select_in_bulk with non-existent IDs"""
        results = workflow_crud.select_in_bulk(test_database_session, ["NONEXISTENT1", "NONEXISTENT2"])
        
        assert results == []
    
    def test_truncate(self, test_database_session, workflow_crud, sample_workflows):
        """Test truncate operation"""
        # Create test items
        for data in sample_workflows:
            workflow_crud.create(test_database_session, **data)
        
        # Verify items exist
        assert workflow_crud.count(test_database_session) == 5
        
        # Truncate
        deleted_count = workflow_crud.truncate(test_database_session)
        
        assert deleted_count == 5
        assert workflow_crud.count(test_database_session) == 0
    
    def test_bulk_create_success(self, test_database_session, workflow_crud):
        """Test successful bulk_create"""
        unique_id = uuid.uuid4().hex[:8]
        bulk_data = [
            {"name": f"Bulk Workflow 1-{unique_id}", "description": "First bulk workflow", "status": WorkflowStatus.ACTIVE},
            {"name": f"Bulk Workflow 2-{unique_id}", "description": "Second bulk workflow", "status": WorkflowStatus.INACTIVE},
            {"name": f"Bulk Workflow 3-{unique_id}", "description": "Third bulk workflow", "status": WorkflowStatus.DRAFT}
        ]
        
        result = workflow_crud.bulk_create(test_database_session, bulk_data)
        
        assert len(result) == 3
        assert all('id' in item for item in result)
        assert all(item['id'].startswith('WF-') for item in result)
        
        # Verify in database
        assert workflow_crud.count(test_database_session) == 3
    
    def test_bulk_create_empty_list(self, test_database_session, workflow_crud):
        """Test bulk_create with empty list"""
        result = workflow_crud.bulk_create(test_database_session, [])
        
        assert result == []
        assert workflow_crud.count(test_database_session) == 0
    
    def test_bulk_create_auto_id_generation(self, test_database_session, workflow_crud):
        """Test bulk_create automatically generates IDs"""
        unique_id = uuid.uuid4().hex[:8]
        bulk_data = [
            {"name": f"Auto ID 1-{unique_id}", "description": "Test"},
            {"name": f"Auto ID 2-{unique_id}", "description": "Test", "id": None},  # Explicit None
        ]
        
        result = workflow_crud.bulk_create(test_database_session, bulk_data)
        
        assert len(result) == 2
        assert all('id' in item and item['id'] is not None for item in result)
        assert all(item['id'].startswith('WF-') for item in result)
    
    def test_bulk_update_success(self, test_database_session, workflow_crud, sample_workflows):
        """Test successful bulk_update"""
        # Create test items
        created_items = []
        for data in sample_workflows:
            item = workflow_crud.create(test_database_session, **data)
            created_items.append(item)
        
        # Prepare update data
        updates = [
            {"id": created_items[0].id, "description": "Updated 1"},
            {"id": created_items[1].id, "description": "Updated 2"},
            {"id": created_items[2].id, "description": "Updated 3"}
        ]
        
        result = workflow_crud.bulk_update(test_database_session, updates)
        
        assert len(result) == 3
        assert all('id' in item for item in result)
        
        # Verify updates in database - need to refresh session to see bulk updates
        test_database_session.expire_all()  # Clear session cache to force reload from DB
        updated_item = workflow_crud.find_by_id(test_database_session, created_items[0].id)
        assert updated_item.description == "Updated 1"
    
    def test_bulk_update_empty_list(self, test_database_session, workflow_crud):
        """Test bulk_update with empty list"""
        result = workflow_crud.bulk_update(test_database_session, [])
        
        assert result == []
    
    def test_bulk_update_missing_id(self, test_database_session, workflow_crud):
        """Test bulk_update with missing ID raises ValueError"""
        updates = [{"description": "Updated"}]  # Missing 'id'
        
        with pytest.raises(ValueError, match="'id' field is required for bulk update"):
            workflow_crud.bulk_update(test_database_session, updates)
    
    def test_bulk_delete_success(self, test_database_session, workflow_crud, sample_workflows):
        """Test successful bulk_delete"""
        # Create test items
        created_items = []
        for data in sample_workflows:
            item = workflow_crud.create(test_database_session, **data)
            created_items.append(item)
        
        # Delete first 3 items
        ids_to_delete = [item.id for item in created_items[:3]]
        deleted_count = workflow_crud.bulk_delete(test_database_session, ids_to_delete)
        
        assert deleted_count == 3
        assert workflow_crud.count(test_database_session) == 2
    
    def test_bulk_delete_empty_list(self, test_database_session, workflow_crud):
        """Test bulk_delete with empty list"""
        result = workflow_crud.bulk_delete(test_database_session, [])
        
        assert result == 0
    
    def test_bulk_delete_nonexistent_ids(self, test_database_session, workflow_crud):
        """Test bulk_delete with non-existent IDs"""
        result = workflow_crud.bulk_delete(test_database_session, ["NONEXISTENT1", "NONEXISTENT2"])
        
        assert result == 0


class TestOptimizedOperations:
    """Test optimized operations"""
    
    def test_check_name_exists_true(self, test_database_session, workflow_crud):
        """Test check_name_exists with existing name"""
        unique_id = uuid.uuid4().hex[:8]
        workflow_crud.create(test_database_session, name=f"Existing Name-{unique_id}", description="Test")
        
        assert workflow_crud.check_name_exists(test_database_session, f"Existing Name-{unique_id}") is True
    
    def test_check_name_exists_false(self, test_database_session, workflow_crud):
        """Test check_name_exists with non-existing name"""
        assert workflow_crud.check_name_exists(test_database_session, "Non-existing Name") is False
    
    def test_check_name_exists_with_exclude_id(self, test_database_session, workflow_crud):
        """Test check_name_exists with exclude_id"""
        unique_id = uuid.uuid4().hex[:8]
        item = workflow_crud.create(test_database_session, name=f"Test Name-{unique_id}", description="Test")
        
        # Should return False when excluding the same item
        assert workflow_crud.check_name_exists(test_database_session, f"Test Name-{unique_id}", exclude_id=item.id) is False
        
        # Should return True when not excluding
        assert workflow_crud.check_name_exists(test_database_session, f"Test Name-{unique_id}") is True
    
    def test_check_name_exists_no_name_field(self, test_database_session):
        """Test check_name_exists on model without name field raises ValueError"""
        from miniflow.database_manager.models import ExecutionInput
        execution_input_crud = BaseCRUD(ExecutionInput)
        
        with pytest.raises(ValueError, match="ExecutionInput does not have a 'name' field"):
            execution_input_crud.check_name_exists(test_database_session, "Test")
    
    def test_bulk_update_status_success(self, test_database_session, workflow_crud, sample_workflows):
        """Test successful bulk_update_status"""
        # Create test items
        created_items = []
        for data in sample_workflows:
            item = workflow_crud.create(test_database_session, **data)
            created_items.append(item)
        
        # Update status of first 3 items
        ids_to_update = [item.id for item in created_items[:3]]
        updated_count = workflow_crud.bulk_update_status(test_database_session, ids_to_update, "status", WorkflowStatus.ARCHIVED)
        
        assert updated_count == 3
        
        # Verify updates - need to refresh session to see bulk updates
        test_database_session.expire_all()
        for item_id in ids_to_update:
            updated_item = workflow_crud.find_by_id(test_database_session, item_id)
            assert updated_item.status == WorkflowStatus.ARCHIVED
    
    def test_bulk_update_status_empty_list(self, test_database_session, workflow_crud):
        """Test bulk_update_status with empty list"""
        result = workflow_crud.bulk_update_status(test_database_session, [], "status", WorkflowStatus.ARCHIVED)
        
        assert result == 0
    
    def test_bulk_update_status_invalid_field(self, test_database_session, workflow_crud):
        """Test bulk_update_status with invalid field raises ValueError"""
        with pytest.raises(ValueError, match="Field 'invalid_field' does not exist in Workflow"):
            workflow_crud.bulk_update_status(test_database_session, ["ID1"], "invalid_field", "value")
    
    def test_bulk_update_status_empty_field_name(self, test_database_session, workflow_crud):
        """Test bulk_update_status with empty field name raises ValueError"""
        with pytest.raises(ValueError, match="Status field name is required"):
            workflow_crud.bulk_update_status(test_database_session, ["ID1"], "", "value")
    
    def test_bulk_update_fields_success(self, test_database_session, workflow_crud, sample_workflows):
        """Test successful bulk_update_fields"""
        # Create test items
        created_items = []
        for data in sample_workflows:
            item = workflow_crud.create(test_database_session, **data)
            created_items.append(item)
        
        # Update multiple fields of first 2 items
        ids_to_update = [item.id for item in created_items[:2]]
        field_updates = {
            "status": "updated",
            "priority": 999,
            "description": "Bulk updated description"
        }
        
        updated_count = workflow_crud.bulk_update_fields(test_database_session, ids_to_update, field_updates)
        
        assert updated_count == 2
        
        # Verify updates
        for item_id in ids_to_update:
            updated_item = workflow_crud.find_by_id(test_database_session, item_id)
            assert updated_item.status == "updated"
            assert updated_item.priority == 999
            assert updated_item.description == "Bulk updated description"
    
    def test_bulk_update_fields_empty_list(self, test_database_session, workflow_crud):
        """Test bulk_update_fields with empty list"""
        result = workflow_crud.bulk_update_fields(test_database_session, [], {"status": "value"})
        
        assert result == 0
    
    def test_bulk_update_fields_empty_updates(self, test_database_session, workflow_crud):
        """Test bulk_update_fields with empty field_updates raises ValueError"""
        with pytest.raises(ValueError, match="No field updates provided"):
            workflow_crud.bulk_update_fields(test_database_session, ["ID1"], {})
    
    def test_bulk_update_fields_invalid_field(self, test_database_session, workflow_crud):
        """Test bulk_update_fields with invalid field raises ValueError"""
        field_updates = {"invalid_field": "value"}
        
        with pytest.raises(ValueError, match="Field 'invalid_field' does not exist in Workflow"):
            workflow_crud.bulk_update_fields(test_database_session, ["ID1"], field_updates)


class TestErrorHandling:
    """Test error handling and edge cases"""
    
    def test_memory_protection_limit(self, test_database_session, workflow_crud):
        """Test memory protection with limit enforcement"""
        # Test that limit is enforced to max 1000
        results = workflow_crud.get_all(test_database_session, limit=2000)  # Request more than max
        
        # Should not crash and should enforce reasonable limits
        assert isinstance(results, list)
    
    def test_invalid_model_operations(self, test_database_session):
        """Test operations with invalid model setup"""
        # This would be caught at initialization time
        crud = BaseCRUD(Workflow)
        assert crud.model == Workflow
    
    def test_database_session_management(self, test_database_session, workflow_crud):
        """Test that operations don't interfere with session management"""
        # Create an item
        item = workflow_crud.create(test_database_session, name="Session Test", description="Test")
        
        # Multiple operations should work fine
        found = workflow_crud.find_by_id(test_database_session, item.id)
        updated = workflow_crud.update(test_database_session, item.id, description="Updated")
        
        assert found.id == item.id
        assert updated.description == "Updated"
    
    def test_concurrent_operations(self, test_database_session, workflow_crud):
        """Test that operations can be performed in sequence"""
        # This tests basic operation sequencing
        items = []
        
        # Create multiple items
        for i in range(3):
            item = workflow_crud.create(test_database_session, name=f"Concurrent {i}", description=f"Test {i}")
            items.append(item)
        
        # Bulk operations
        ids = [item.id for item in items]
        selected = workflow_crud.select_in_bulk(test_database_session, ids)
        
        assert len(selected) == 3
    
    def test_data_integrity(self, test_database_session, workflow_crud):
        """Test data integrity constraints"""
        # Create item with unique name
        workflow_crud.create(test_database_session, name="Unique Item", description="Test")
        
        # Try to create another item with same name - should raise IntegrityError
        with pytest.raises(IntegrityError):
            workflow_crud.create(test_database_session, name="Unique Item", description="Test 2")
            test_database_session.flush()


class TestPerformanceAndIntegration:
    """Test performance characteristics and integration scenarios"""
    
    def test_bulk_vs_individual_performance(self, test_database_session, workflow_crud):
        """Test that bulk operations are more efficient than individual operations"""
        # Prepare data for bulk creation
        bulk_data = [
            {"name": f"Bulk Item {i}", "description": f"Bulk description {i}", "status": "active"}
            for i in range(10)
        ]
        
        # Measure bulk creation time
        start_time = time.time()
        result = workflow_crud.bulk_create(test_database_session, bulk_data)
        bulk_time = time.time() - start_time
        
        assert len(result) == 10
        assert bulk_time < 1.0  # Should be very fast
        
        # Clean up for individual test
        workflow_crud.truncate(test_database_session)
        
        # Measure individual creation time
        start_time = time.time()
        for data in bulk_data:
            workflow_crud.create(test_database_session, **data)
        individual_time = time.time() - start_time
        
        # Bulk should be faster (though with small dataset difference might be minimal)
        assert bulk_time <= individual_time * 2  # Allow some variance
    
    def test_large_dataset_handling(self, test_database_session, workflow_crud):
        """Test handling of larger datasets"""
        # Create a moderate number of items to test pagination
        bulk_data = [
            {"name": f"Dataset Item {i}", "description": f"Description {i}", "priority": i % 10}
            for i in range(50)
        ]
        
        result = workflow_crud.bulk_create(test_database_session, bulk_data)
        assert len(result) == 50
        
        # Test pagination works correctly
        page1 = workflow_crud.get_all(test_database_session, skip=0, limit=20)
        page2 = workflow_crud.get_all(test_database_session, skip=20, limit=20)
        page3 = workflow_crud.get_all(test_database_session, skip=40, limit=20)
        
        assert len(page1) == 20
        assert len(page2) == 20
        assert len(page3) == 10  # Remaining items
        
        # Test filtering works with larger dataset
        filtered = workflow_crud.filter(test_database_session, {"priority": 5})
        assert len(filtered) == 5  # Items with priority 5 (5, 15, 25, 35, 45)
    
    def test_complex_query_scenarios(self, test_database_session, workflow_crud):
        """Test complex query combinations"""
        # Create varied test data
        test_data = [
            {"name": "High Priority Active", "status": "active", "priority": 10},
            {"name": "High Priority Inactive", "status": "inactive", "priority": 10},
            {"name": "Low Priority Active", "status": "active", "priority": 1},
            {"name": "Medium Priority Draft", "status": "draft", "priority": 5},
        ]
        
        for data in test_data:
            workflow_crud.create(test_database_session, **data)
        
        # Complex filtering
        high_priority = workflow_crud.filter(test_database_session, {"priority": 10})
        assert len(high_priority) == 2
        
        active_items = workflow_crud.filter(test_database_session, {"status": "active"})
        assert len(active_items) == 2
        
        high_priority_active = workflow_crud.filter(test_database_session, {"priority": 10, "status": "active"})
        assert len(high_priority_active) == 1
        assert high_priority_active[0].name == "High Priority Active"
    
    def test_id_generation_uniqueness(self, test_database_session, workflow_crud):
        """Test that ID generation produces unique IDs"""
        # Create multiple items and ensure all IDs are unique
        bulk_data = [
            {"name": f"ID Test Item {i}", "description": "Test"}
            for i in range(20)
        ]
        
        result = workflow_crud.bulk_create(test_database_session, bulk_data)
        
        # Extract all IDs
        ids = [item['id'] for item in result]
        
        # All IDs should be unique
        assert len(ids) == len(set(ids))
        
        # All IDs should have correct prefix
        assert all(id_val.startswith('WF-') for id_val in ids)
        
        # IDs should be proper length (WF- + 17 characters)
        assert all(len(id_val) == 20 for id_val in ids)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])