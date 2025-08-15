import pytest

from miniflow.database.models import Workflow, WorkflowStatus
from miniflow.exceptions import CRUDException


@pytest.fixture
def sample_workflow_data():
    """Test için sample workflow data"""
    return {
        "name": "test_workflow",
        "description": "Test workflow description",
        "priority": 5,
    }

@pytest.fixture
def invalid_workflow_data():
    """Test için sample workflow data"""
    return {
        "name": "test_workflow",
        "description": "Test workflow description",
        "priority": 5,
        "random_col": 4
    }

@pytest.fixture
def multiple_workflow_data():
    """Multiple workflow data for bulk operations"""
    return [
        {"name": "workflow_1", "description": "First workflow", "priority": 1, "status": WorkflowStatus.DRAFT},
        {"name": "workflow_2", "description": "Second workflow", "priority": 5, "status": WorkflowStatus.ACTIVE},
        {"name": "workflow_3", "description": "Third workflow", "priority": 10, "status": WorkflowStatus.DRAFT},
        {"name": "workflow_4", "description": "Fourth workflow", "priority": 3, "status": WorkflowStatus.ACTIVE},
        {"name": "workflow_5", "description": "Fif th workflow", "priority": 7, "status": WorkflowStatus.DRAFT},
    ]


@pytest.mark.unittest
class TestWorkflowCrudBasic:
    """Temel CRUD işlemleri testleri"""
    def test_workflow_crud_initialization(self, workflow_crud):
        assert workflow_crud.model == Workflow
        assert workflow_crud.model_name == "Workflow"

    def test_create_workflow_valid_data(self, clean_db, workflow_crud, sample_workflow_data):
        workflow = workflow_crud.create_workflow(clean_db, **sample_workflow_data)

        assert workflow is not None
        assert workflow.id is not None
        assert workflow.id.startswith("WF-")
        assert workflow.created_at is not None
        assert workflow.updated_at is not None
        assert workflow.name == "test_workflow"
        assert workflow.description == "Test workflow description"
        assert workflow.priority == 5
        assert workflow.status == WorkflowStatus.DRAFT
        assert workflow.execution_count == 0
        assert workflow.last_executed_at is None
        assert workflow.last_execution_duration is None

    def test_create_workflow_invalid_data(self, clean_db, workflow_crud, invalid_workflow_data):
        """Geçersiz alanlar ile workflow oluşturma testi - geçersiz alanlar filtrelenir"""
        workflow = workflow_crud.create_workflow(clean_db, **invalid_workflow_data)

        assert workflow is not None
        assert workflow.id is not None
        assert workflow.id.startswith("WF-")
        assert workflow.created_at is not None
        assert workflow.updated_at is not None
        assert workflow.name == "test_workflow"
        assert workflow.description == "Test workflow description"
        assert workflow.priority == 5
        assert workflow.status == WorkflowStatus.DRAFT
        assert workflow.execution_count == 0
        assert workflow.last_executed_at is None
        assert workflow.last_execution_duration is None
        
        # Geçersiz alanın filtrelendiğini doğrula
        assert not hasattr(workflow, 'random_col')

    def test_update_workflow_valid_data(self, clean_db, workflow_crud, sample_workflow_data):
        workflow = workflow_crud.create_workflow(clean_db, **sample_workflow_data)

        update_payload = {
            "description": "Updated description",
            "priority": 10
        }

        updated_workflow = workflow_crud.update_workflow(clean_db, workflow.id, **update_payload)

        assert updated_workflow.id == workflow.id
        assert updated_workflow.name == workflow.name
        assert updated_workflow.description == "Updated description"
        assert updated_workflow.priority == 10
        assert updated_workflow.status == WorkflowStatus.DRAFT
        assert updated_workflow.updated_at != workflow.created_at

    def test_update_workflow_invalid_data(self, clean_db, workflow_crud, sample_workflow_data):
        workflow = workflow_crud.create_workflow(clean_db, **sample_workflow_data)

        invalid_update_payload = {
            "description": "Updated description",
            "priority": 10,
            "random_col":6
        }

        updated_workflow = workflow_crud.update_workflow(clean_db, workflow.id, **invalid_update_payload)

        assert updated_workflow.id == workflow.id
        assert updated_workflow.name == workflow.name
        assert updated_workflow.description == "Updated description"
        assert updated_workflow.priority == 10
        assert updated_workflow.status == WorkflowStatus.DRAFT
        assert updated_workflow.updated_at != workflow.created_at

    def test_update_workflow_invalid_id(self, clean_db, workflow_crud, sample_workflow_data):
        with pytest.raises(CRUDException) as exc_info:
            workflow_crud.update_workflow(clean_db, "WF-NONEXISTENT123", **sample_workflow_data)
        assert "No such record" in str(exc_info.value)

    def test_delete_workflow_valid_id(self, clean_db, workflow_crud, sample_workflow_data):
        workflow = workflow_crud.create_workflow(clean_db, **sample_workflow_data)
        deleted_workflow = workflow_crud.delete_workflow(clean_db, workflow.id)

        assert deleted_workflow is not None
        assert deleted_workflow.id == workflow.id
        assert deleted_workflow.name == workflow.name
        assert deleted_workflow.description == workflow.description
        assert deleted_workflow.status == workflow.status
        assert deleted_workflow.updated_at == workflow.updated_at
        assert deleted_workflow.created_at == workflow.created_at

    def test_delete_workflow_invalid_id(self, clean_db, workflow_crud):
        with pytest.raises(CRUDException) as exc_info:
            workflow_crud.delete_workflow(clean_db, "WF-NONEXISTENT123")
        assert "No such record" in str(exc_info.value)

    def test_find_by_id_valid(self, clean_db, workflow_crud, sample_workflow_data):
        workflow = workflow_crud.create_workflow(clean_db, **sample_workflow_data)
        find_by_id = workflow_crud.find_by_id(clean_db, workflow.id)

        assert find_by_id is not None
        assert find_by_id.id == workflow.id
        assert find_by_id.name == workflow.name

    def test_find_by_id_invalid(self, clean_db, workflow_crud):
        workflow = workflow_crud.find_by_id(clean_db, "WF-NONEXISTENT123")
        assert workflow is None

@pytest.mark.unittest
class TestWorkflowCrudBusiness:
    """İş mantığı işlemleri testleri"""
    def test_set_priority_valid_range(self, clean_db, workflow_crud, sample_workflow_data):
        workflow = workflow_crud.create_workflow(clean_db, **sample_workflow_data)

        for priority in [0, 5, 10]:
            updated_workflow = workflow_crud.set_priority(clean_db, workflow.id, priority)
            assert updated_workflow.priority == priority

    def test_set_priority_invalid_range(self, clean_db, workflow_crud, sample_workflow_data):
        workflow = workflow_crud.create_workflow(clean_db, **sample_workflow_data)

        # Test invalid priorities
        invalid_priorities = [-1, 11, 100]
        for priority in invalid_priorities:
            with pytest.raises(ValueError, match="Priority must be between 0 and 10"):
                workflow_crud.set_priority(clean_db, workflow.id, priority)

    def test_set_status_active(self, clean_db, workflow_crud, sample_workflow_data):
        workflow = workflow_crud.create_workflow(clean_db, **sample_workflow_data)

        active_workflow = workflow_crud.set_status_active(clean_db, workflow.id)
        assert active_workflow.status == WorkflowStatus.ACTIVE

    def test_set_status_draft(self, clean_db, workflow_crud, sample_workflow_data):
        workflow = workflow_crud.create_workflow(clean_db, **sample_workflow_data)

        active_workflow = workflow_crud.set_status_draft(clean_db, workflow.id)
        assert active_workflow.status == WorkflowStatus.DRAFT

    def test_get_workflow_by_name(self, clean_db, workflow_crud, sample_workflow_data):
        workflow = workflow_crud.create_workflow(clean_db, **sample_workflow_data)
        find_by_name = workflow_crud.find_by_name(clean_db, workflow.name)

        assert find_by_name is not None
        assert find_by_name.id == workflow.id
        assert find_by_name.name == workflow.name

    def test_get_workflow_by_invalid_name(self, clean_db, workflow_crud, sample_workflow_data):
        with pytest.raises(CRUDException) as exc_info:
            find_by_name = workflow_crud.find_by_name(clean_db, "random_name")
        assert "No such record" in str(exc_info.value)

    def test_get_active_workflows(self, clean_db, workflow_crud, sample_workflow_data):
        workflows = workflow_crud.get_active_workflows(clean_db)
        assert len(workflows) == 0

        workflow_payload_1 = {
            "name": "test_workflow_1",
            "description": "Test workflow description",
            "priority": 5,
            "status": WorkflowStatus.ACTIVE,
        }
        workflow_crud.create_workflow(clean_db, **workflow_payload_1)
        workflows = workflow_crud.get_active_workflows(clean_db)
        assert len(workflows) == 1

        workflow_payload_2 = {
            "name": "test_workflow_2",
            "description": "Test workflow description",
            "priority": 5,
            "status": WorkflowStatus.ACTIVE,
        }
        workflow_crud.create_workflow(clean_db, **workflow_payload_2)
        workflows = workflow_crud.get_active_workflows(clean_db)
        assert len(workflows) == 2

    def test_get_draft_workflows(self, clean_db, workflow_crud, sample_workflow_data):
        workflows = workflow_crud.get_draft_workflows(clean_db)
        assert len(workflows) == 0

        workflow_payload_1 = {
            "name": "test_workflow_1",
            "description": "Test workflow description",
            "priority": 5,
            "status": WorkflowStatus.DRAFT,
        }
        workflow_crud.create_workflow(clean_db, **workflow_payload_1)
        workflows = workflow_crud.get_draft_workflows(clean_db)
        assert len(workflows) == 1

        workflow_payload_2 = {
            "name": "test_workflow_2",
            "description": "Test workflow description",
            "priority": 5,
            "status": WorkflowStatus.DRAFT,
        }
        workflow_crud.create_workflow(clean_db, **workflow_payload_2)
        workflows = workflow_crud.get_draft_workflows(clean_db)
        assert len(workflows) == 2

    def test_workflow_count(self, clean_db, workflow_crud, sample_workflow_data):
        res = workflow_crud.count(clean_db)
        assert res == 0

        workflow_payload_1 = {
            "name": "test_workflow_1",
            "description": "Test workflow description",
            "priority": 5,
            "status": WorkflowStatus.ACTIVE,
        }
        workflow_crud.create_workflow(clean_db, **workflow_payload_1)
        res = workflow_crud.count(clean_db)
        assert res == 1

        workflow_payload_2 = {
            "name": "test_workflow_2",
            "description": "Test workflow description",
            "priority": 5,
            "status": WorkflowStatus.DRAFT,
        }
        workflow_crud.create_workflow(clean_db, **workflow_payload_2)
        res = workflow_crud.count(clean_db)
        assert res == 2

    def test_workflow_get_all_basic(self, clean_db, workflow_crud, sample_workflow_data):
        workflow_crud.create_workflow(clean_db, **sample_workflow_data)

        workflow_payload_1 = {
            "name": "test_workflow_1",
            "description": "Test workflow description",
            "priority": 7,
            "status": WorkflowStatus.DRAFT,
        }
        workflow_crud.create_workflow(clean_db, **workflow_payload_1)

        workflow_payload_2 = {
            "name": "test_workflow_2",
            "description": "Test workflow description",
            "priority": 10,
            "status": WorkflowStatus.DRAFT,
        }
        workflow_crud.create_workflow(clean_db, **workflow_payload_2)

        results = workflow_crud.get_all(clean_db)
        assert len(results) == 3

    def test_workflow_get_all_order_by_priority(self, clean_db, workflow_crud, sample_workflow_data):
        workflow_crud.create_workflow(clean_db, **sample_workflow_data)

        workflow_payload_1 = {
            "name": "test_workflow_1",
            "description": "Test workflow description",
            "priority": 5,
            "status": WorkflowStatus.DRAFT,
        }
        workflow_crud.create_workflow(clean_db, **workflow_payload_1)

        workflow_payload_2 = {
            "name": "test_workflow_2",
            "description": "Test workflow description",
            "priority": 5,
            "status": WorkflowStatus.DRAFT,
        }
        workflow_crud.create_workflow(clean_db, **workflow_payload_2)

        results = workflow_crud.get_all(clean_db, order_by="priority")
        priorities = [u.priority for u in results]
        assert priorities == sorted(priorities, reverse=True)

    def test_workflow_exists_with_valid_id(self, clean_db, workflow_crud, sample_workflow_data):
        workflow = workflow_crud.create(clean_db, **sample_workflow_data)
        res = workflow_crud.exists(clean_db, workflow.id)
        assert res == True

    def test_workflow_exists_with_invalid_id(self, clean_db, workflow_crud, sample_workflow_data):
        res = workflow_crud.exists(clean_db, "random_id")
        assert res == False

    def test_truncate_workflows(self, clean_db, workflow_crud, multiple_workflow_data):
        """Truncate method testi"""
        # Create workflows first
        workflow_crud.bulk_create(clean_db, multiple_workflow_data)
        assert workflow_crud.count(clean_db) == 5

        # ACTION
        deleted_count = workflow_crud.truncate(clean_db)

        # ASSERTION
        assert deleted_count == 5
        assert workflow_crud.count(clean_db) == 0

    def test_truncate_empty_table(self, clean_db, workflow_crud):
        """Boş tablo truncate testi"""
        result = workflow_crud.truncate(clean_db)
        assert result == 0

@pytest.mark.unittest
class TestWorkflowAdvancedBusiness:
    """İş mantığı işlemleri testleri"""

    def test_bulk_create_workflows(self, clean_db, workflow_crud, multiple_workflow_data):
        """Bulk create workflows testi"""
        # ACTION
        created_workflows = workflow_crud.bulk_create(clean_db, multiple_workflow_data)

        # ASSERTION
        assert len(created_workflows) == 5
        assert all('id' in workflow for workflow in created_workflows)
        assert all(workflow['id'].startswith('WF-') for workflow in created_workflows)

        # Verify in database
        all_workflows = workflow_crud.get_all(clean_db)
        assert len(all_workflows) == 5

    def test_bulk_create_empty_list(self, clean_db, workflow_crud):
        """Bulk create with empty list"""
        result = workflow_crud.bulk_create(clean_db, [])
        assert result == []

    def test_bulk_create_with_existing_ids(self, clean_db, workflow_crud):
        """Bulk create with pre-existing IDs"""
        workflows_with_ids = [
            {"id": "WF-TEST123456789", "name": "test1", "description": "Test 1", "priority": 1},
            {"id": "WF-TEST987654321", "name": "test2", "description": "Test 2", "priority": 2},
        ]

        created = workflow_crud.bulk_create(clean_db, workflows_with_ids)
        assert len(created) == 2
        assert created[0]['id'] == "WF-TEST123456789"
        assert created[1]['id'] == "WF-TEST987654321"

    def test_bulk_update_workflows(self, clean_db, workflow_crud, multiple_workflow_data):
        """Bulk update workflows testi"""
        # Create workflows first
        created_workflows = workflow_crud.bulk_create(clean_db, multiple_workflow_data)

        # Prepare update data
        update_data = [
            {"id": created_workflows[0]['id'], "priority": 9, "description": "Updated 1"},
            {"id": created_workflows[1]['id'], "priority": 8, "description": "Updated 2"},
        ]

        # ACTION
        updated = workflow_crud.bulk_update(clean_db, update_data)

        # ASSERTION
        assert len(updated) == 2

        # Verify updates
        workflow1 = workflow_crud.find_by_id(clean_db, created_workflows[0]['id'])
        workflow2 = workflow_crud.find_by_id(clean_db, created_workflows[1]['id'])

        assert workflow1.priority == 9
        assert workflow1.description == "Updated 1"
        assert workflow2.priority == 8
        assert workflow2.description == "Updated 2"

    def test_bulk_update_without_id(self, clean_db, workflow_crud):
        """Bulk update without ID should raise error"""
        with pytest.raises(ValueError, match="'id' field is required"):
            workflow_crud.bulk_update(clean_db, [{"name": "test"}])

    def test_bulk_delete_workflows(self, clean_db, workflow_crud, multiple_workflow_data):
        """Bulk delete workflows testi"""
        # Create workflows first
        created_workflows = workflow_crud.bulk_create(clean_db, multiple_workflow_data)
        workflow_ids = [w['id'] for w in created_workflows[:3]]  # Delete first 3

        # ACTION
        deleted_count = workflow_crud.bulk_delete(clean_db, workflow_ids)

        # ASSERTION
        assert deleted_count == 3

        # Verify remaining workflows
        remaining = workflow_crud.get_all(clean_db)
        assert len(remaining) == 2

    def test_bulk_delete_empty_list(self, clean_db, workflow_crud):
        """Bulk delete with empty list"""
        result = workflow_crud.bulk_delete(clean_db, [])
        assert result == 0

    def test_select_in_bulk(self, clean_db, workflow_crud, multiple_workflow_data):
        """Select workflows in bulk testi"""
        # Create workflows first
        created_workflows = workflow_crud.bulk_create(clean_db, multiple_workflow_data)
        workflow_ids = [w['id'] for w in created_workflows[:3]]

        # ACTION
        selected_workflows = workflow_crud.select_in_bulk(clean_db, workflow_ids)

        # ASSERTION
        assert len(selected_workflows) == 3
        assert all(wf.id in workflow_ids for wf in selected_workflows)

    def test_select_in_bulk_empty_list(self, clean_db, workflow_crud):
        """Select in bulk with empty list"""
        result = workflow_crud.select_in_bulk(clean_db, [])
        assert result == []

    def test_select_in_bulk_nonexistent_ids(self, clean_db, workflow_crud):
        """Select in bulk with nonexistent IDs"""
        result = workflow_crud.select_in_bulk(clean_db, ["WF-NONEXISTENT1", "WF-NONEXISTENT2"])
        assert result == []

    def test_bulk_update_status(self, clean_db, workflow_crud, multiple_workflow_data):
        """Bulk status update testi"""
        # Create workflows first
        created_workflows = workflow_crud.bulk_create(clean_db, multiple_workflow_data)
        workflow_ids = [w['id'] for w in created_workflows[:3]]

        # ACTION
        updated_count = workflow_crud.bulk_update_status(
            clean_db, workflow_ids, "status", WorkflowStatus.ACTIVE
        )

        # ASSERTION
        assert updated_count == 3

        # Verify updates
        for workflow_id in workflow_ids:
            workflow = workflow_crud.find_by_id(clean_db, workflow_id)
            assert workflow.status == WorkflowStatus.ACTIVE

    def test_bulk_update_status_invalid_field(self, clean_db, workflow_crud):
        """Geçersiz field ile bulk update status"""
        with pytest.raises(ValueError, match="Field 'invalid_field' does not exist"):
            workflow_crud.bulk_update_status(clean_db, ["WF-TEST123"], "invalid_field", "value")

    def test_bulk_update_fields(self, clean_db, workflow_crud, multiple_workflow_data):
        """Bulk fields update testi"""
        # Create workflows first
        created_workflows = workflow_crud.bulk_create(clean_db, multiple_workflow_data)
        workflow_ids = [w['id'] for w in created_workflows[:2]]

        # ACTION
        field_updates = {
            "priority": 9,
            "description": "Bulk updated description"
        }
        updated_count = workflow_crud.bulk_update_fields(clean_db, workflow_ids, field_updates)

        # ASSERTION
        assert updated_count == 2

        # Verify updates
        for workflow_id in workflow_ids:
            workflow = workflow_crud.find_by_id(clean_db, workflow_id)
            assert workflow.priority == 9
            assert workflow.description == "Bulk updated description"

    def test_bulk_update_fields_invalid_field(self, clean_db, workflow_crud):
        """Geçersiz field ile bulk update fields"""
        with pytest.raises(ValueError, match="Field 'invalid_field' does not exist"):
            workflow_crud.bulk_update_fields(clean_db, ["WF-TEST123"], {"invalid_field": "value"})

@pytest.mark.unittest
class TestWorkflowCRUDFilteringAndPagination:
    """WorkflowCRUD filtering and pagination testleri"""

    def test_filter_by_single_criteria(self, clean_db, workflow_crud, multiple_workflow_data):
        """Filter by single criteria testi"""
        workflow_crud.bulk_create(clean_db, multiple_workflow_data)

        # Filter by status
        active_workflows = workflow_crud.filter(clean_db, {"status": WorkflowStatus.ACTIVE})
        assert len(active_workflows) == 2

        # Filter by priority
        high_priority_workflows = workflow_crud.filter(clean_db, {"priority": 10})
        assert len(high_priority_workflows) == 1
        assert high_priority_workflows[0].name == "workflow_3"

    def test_filter_by_multiple_criteria(self, clean_db, workflow_crud, multiple_workflow_data):
        """Filter by multiple criteria testi"""
        workflow_crud.bulk_create(clean_db, multiple_workflow_data)

        # Filter by status and priority
        workflows = workflow_crud.filter(clean_db, {
            "status": WorkflowStatus.DRAFT,
            "priority": 1
        })
        assert len(workflows) == 1
        assert workflows[0].name == "workflow_1"

    def test_filter_with_invalid_field(self, clean_db, workflow_crud):
        """Filter with invalid field should raise error"""
        with pytest.raises(ValueError, match="Field 'invalid_field' does not exist"):
            workflow_crud.filter(clean_db, {"invalid_field": "value"})

    def test_filter_with_pagination(self, clean_db, workflow_crud, multiple_workflow_data):
        """Filter with pagination testi"""
        workflow_crud.bulk_create(clean_db, multiple_workflow_data)

        # Test limit
        limited_workflows = workflow_crud.filter(clean_db, {}, limit=3)
        assert len(limited_workflows) == 3

        # Test skip
        skipped_workflows = workflow_crud.filter(clean_db, {}, skip=2, limit=2)
        assert len(skipped_workflows) == 2

        # Test skip + limit
        paginated_workflows = workflow_crud.filter(clean_db, {}, skip=1, limit=2)
        assert len(paginated_workflows) == 2

    def test_filter_with_order_by(self, clean_db, workflow_crud, multiple_workflow_data):
        """Filter with ordering testi"""
        workflow_crud.bulk_create(clean_db, multiple_workflow_data)

        # Order by priority ascending
        workflows = workflow_crud.filter(clean_db, {}, order_by_field="priority")
        priorities = [wf.priority for wf in workflows]
        assert priorities == sorted(priorities)

        # Order by name
        workflows = workflow_crud.filter(clean_db, {}, order_by_field="name")
        names = [wf.name for wf in workflows]
        assert names == sorted(names)

    def test_filter_with_invalid_order_by(self, clean_db, workflow_crud, multiple_workflow_data):
        """Filter with invalid order by field"""
        workflow_crud.bulk_create(clean_db, multiple_workflow_data)

        # Should fall back to id ordering
        workflows = workflow_crud.filter(clean_db, {}, order_by_field="invalid_field")
        assert len(workflows) == 5

    def test_count_filtered(self, clean_db, workflow_crud, multiple_workflow_data):
        """Count filtered records testi"""
        workflow_crud.bulk_create(clean_db, multiple_workflow_data)

        # Count by status
        active_count = workflow_crud.count_filtered(clean_db, {"status": WorkflowStatus.ACTIVE})
        assert active_count == 2

        # Count by priority
        high_priority_count = workflow_crud.count_filtered(clean_db, {"priority": 10})
        assert high_priority_count == 1

    def test_memory_protection_limit(self, clean_db, workflow_crud):
        """Test memory protection limit (max 1000)"""
        # Create more than 1000 workflows
        workflows_data = []
        for i in range(1100):
            workflows_data.append({
                "name": f"workflow_{i}",
                "description": f"Workflow {i}",
                "priority": i % 11
            })

        workflow_crud.bulk_create(clean_db, workflows_data)

        # Test that limit is enforced
        result = workflow_crud.filter(clean_db, {}, limit=1500)
        assert len(result) == 1000  # Should be capped at 1000


