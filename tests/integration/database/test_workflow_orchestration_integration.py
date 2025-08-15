"""
Integration tests for WorkflowOrchestrator with WorkflowCRUD
Tests the complete flow from orchestration layer to database
"""

import pytest

from miniflow.database.orchestration.workflow_orchestration import WorkflowOrchestrator
from miniflow.exceptions import ValidationError, BusinessLogicError
from miniflow.database.models import Workflow, WorkflowStatus


@pytest.fixture
def workflow_orchestrator():
    """ Real WorkflowOrchestrator instance """
    return WorkflowOrchestrator()

@pytest.fixture
def sample_workflow_data():
    """ Sample workflow data for testing """
    return {
        'name': 'test_orchestration_workflow',
        'description': 'Integration test workflow for orchestration',
        'priority': 5
    }

@pytest.fixture
def invalid_workflow_data():
    """ Sample workflow data for testing """
    return {
        'name': 'test_orchestration_workflow',
        'description': 'Integration test workflow for orchestration',
        'priority': 5,
        'invalid_col': "ERROR"
    }

@pytest.fixture
def missing_workflow_data():
    """ Sample workflow data for testing """
    return {
        'description': 'Integration test workflow for orchestration',
        'priority': 5,
        'invalid_col': "ERROR"
    }


@pytest.fixture
def sample_workflow_data_batch():
    """ Sample workflow data batch for testing """
    return [
        {
            'name': 'workflow_batch_1',
            'description': 'First batch workflow',
            'priority': 1
        },
        {
            'name': 'workflow_batch_2',
            'description': 'Second batch workflow',
            'priority': 8
        },
        {
            'name': 'workflow_batch_3',
            'description': 'Third batch workflow',
            'priority': 3
        }
    ]


@pytest.mark.integration
class TestWorkflowOrchestrationCreate:
    def test_create_workflow_with_valid_data(self, clean_db, workflow_orchestrator, sample_workflow_data):
        result = workflow_orchestrator.create(clean_db, sample_workflow_data)

        # Verify the result
        assert type(result) == dict
        assert result is not None
        assert 'id' in result
        assert result['name'] == sample_workflow_data['name']
        assert result['description'] == sample_workflow_data['description']
        assert result['priority'] == sample_workflow_data['priority']
        assert result['status'] == WorkflowStatus.DRAFT
        assert 'execution_count' in result
        assert 'last_executed_at' in result
        assert 'last_execution_duration' in result

        # Verify the database
        workflow = clean_db.get(Workflow, result['id'])
        assert workflow is not None
        assert workflow.name == sample_workflow_data['name']
        assert workflow.description == sample_workflow_data['description']
        assert workflow.priority == sample_workflow_data['priority']

    def test_create_workflow_with_duplicate_name(self, clean_db, workflow_orchestrator, sample_workflow_data):
        workflow_orchestrator.create(clean_db, sample_workflow_data)

        with pytest.raises(ValidationError, match="Workflow with name 'test_orchestration_workflow' already exists"):
            workflow_orchestrator.create(clean_db, sample_workflow_data)

    def test_create_workflow_with_invalid_data(self, clean_db, workflow_orchestrator, invalid_workflow_data):
        result = workflow_orchestrator.create(clean_db, invalid_workflow_data)

        # Verify the result
        assert result is not None
        assert 'id' in result
        assert result['name'] == invalid_workflow_data['name']
        assert result['description'] == invalid_workflow_data['description']
        assert result['priority'] == invalid_workflow_data['priority']
        assert result['status'] == WorkflowStatus.DRAFT
        assert 'execution_count' in result
        assert 'last_executed_at' in result
        assert 'last_execution_duration' in result

        # Verify the database
        workflow = clean_db.get(Workflow, result['id'])
        assert workflow is not None
        assert workflow.name == invalid_workflow_data['name']
        assert workflow.description == invalid_workflow_data['description']
        assert workflow.priority == invalid_workflow_data['priority']

    def test_create_workflow_with_missing_data(self, clean_db, workflow_orchestrator, missing_workflow_data):
        with pytest.raises(KeyError) as exc_info:
            workflow_orchestrator.create(clean_db, missing_workflow_data)

@pytest.mark.integration
class TestWorkflowOrchestrationUpdate:
    def test_update_workflow_with_valid_data(self, clean_db, workflow_orchestrator, sample_workflow_data):
        workflow =  workflow_orchestrator.create(clean_db, sample_workflow_data)

        update_data = {
            'description': 'Updated description via orchestration',
            'priority': 9
        }

        updated_workflow = workflow_orchestrator.update(clean_db, workflow['id'], update_data)

        assert updated_workflow is not None
        assert updated_workflow['id'] == workflow['id']
        assert updated_workflow['description'] == update_data['description']
        assert updated_workflow['priority'] == update_data['priority']
        assert updated_workflow['status'] == workflow['status']
        assert 'execution_count' in updated_workflow
        assert 'last_executed_at' in updated_workflow
        assert 'last_execution_duration' in updated_workflow

    def test_update_workflow_with_duplicate_name(self, clean_db, workflow_orchestrator, sample_workflow_data):
        # Create first workflow
        workflow1 = workflow_orchestrator.create(clean_db, sample_workflow_data)
        
        # Create second workflow with different name
        workflow2_data = {
            'name': 'second_workflow',
            'description': 'Second workflow',
            'priority': 3
        }
        workflow2 = workflow_orchestrator.create(clean_db, workflow2_data)
        
        # Try to update second workflow with first workflow's name
        update_data = {'name': sample_workflow_data['name']}
        
        with pytest.raises(ValidationError, match="Workflow with name 'test_orchestration_workflow' already exists"):
            workflow_orchestrator.update(clean_db, workflow2['id'], update_data)

    def test_update_workflow_with_invalid_id(self, clean_db, workflow_orchestrator, sample_workflow_data):
        with pytest.raises(BusinessLogicError) as exc_info:
            workflow_orchestrator.update(clean_db, 'WF-123', {'name':'test_2'})

    def test_update_workflow_with_invalid_data(self, clean_db, workflow_orchestrator, sample_workflow_data):
        # Create a workflow first
        workflow = workflow_orchestrator.create(clean_db, sample_workflow_data)
        
        # Update with invalid fields (should be filtered out by BaseCRUD)
        update_data = {
            'description': 'Updated description',
            'priority': 7,
            'invalid_field': 'should_be_ignored'
        }
        
        updated_workflow = workflow_orchestrator.update(clean_db, workflow['id'], update_data)
        
        assert updated_workflow is not None
        assert updated_workflow['description'] == update_data['description']
        assert updated_workflow['priority'] == update_data['priority']
        # Invalid field should not be in the result
        assert 'invalid_field' not in updated_workflow

    def test_update_workflow_with_missing_data(self, clean_db, workflow_orchestrator, sample_workflow_data):
        # Create a workflow first
        workflow = workflow_orchestrator.create(clean_db, sample_workflow_data)
        
        # Update with empty data should raise error
        with pytest.raises(ValueError, match="No data provided for database update"):
            workflow_orchestrator.update(clean_db, workflow['id'], {})

@pytest.mark.integration
class TestWorkflowOrchestrationDelete:
    def test_delete_workflow_with_valid_id(self, clean_db, workflow_orchestrator, sample_workflow_data):
        workflow = workflow_orchestrator.create(clean_db, sample_workflow_data)

        deleted_workflow = workflow_orchestrator.delete(clean_db, workflow['id'])

        assert deleted_workflow is not None
        assert deleted_workflow['id'] == workflow['id']
        assert deleted_workflow['description'] == workflow['description']
        assert deleted_workflow['priority'] == workflow['priority']

    def test_delete_workflow_with_invalid_id(self, clean_db, workflow_orchestrator):
        with pytest.raises(BusinessLogicError) as exc_info:
            workflow_orchestrator.delete(clean_db, 'WF-123')

@pytest.mark.integration
class TestWorkflowOrchestrationSearch:
    def test_search_workflow_with_one_criteria(self, clean_db, workflow_orchestrator, sample_workflow_data_batch):
        for workflow_data in sample_workflow_data_batch:
            workflow_orchestrator.create(clean_db, workflow_data)

        search_result = workflow_orchestrator.search(clean_db, {'priority': 8})

        assert search_result['total_count'] == 1
        assert len(search_result['data']) == 1
        assert search_result['data'][0]['priority'] == 8
        assert search_result['data'][0]['name'] == 'workflow_batch_2'
        assert search_result['skip'] == 0
        assert search_result['limit'] == 100
        assert search_result['has_more'] is False

    def test_search_workflow_with_two_criteria(self, clean_db, workflow_orchestrator, sample_workflow_data_batch):
        # Add a workflow with priority 3 and status ACTIVE
        extra_workflow_data = {
            'name': 'workflow_active_priority_3',
            'description': 'Active workflow with priority 3',
            'priority': 3
        }
        
        for workflow_data in sample_workflow_data_batch:
            workflow_orchestrator.create(clean_db, workflow_data)
        
        extra_workflow = workflow_orchestrator.create(clean_db, extra_workflow_data)
        workflow_orchestrator.set_status_active(clean_db, extra_workflow['id'])
        
        # Search with two criteria: priority=3 and status=ACTIVE
        search_result = workflow_orchestrator.search(clean_db, {
            'priority': 3, 
            'status': WorkflowStatus.ACTIVE
        })
        
        assert search_result['total_count'] == 1
        assert len(search_result['data']) == 1
        assert search_result['data'][0]['priority'] == 3
        assert search_result['data'][0]['status'] == WorkflowStatus.ACTIVE
        assert search_result['data'][0]['name'] == 'workflow_active_priority_3'

    def test_search_workflow_with_invalid_criteria(self, clean_db, workflow_orchestrator, sample_workflow_data):
        # Create a workflow first
        workflow_orchestrator.create(clean_db, sample_workflow_data)
        
        # Search with invalid field should raise ValueError
        with pytest.raises(ValueError, match="Field 'invalid_field' does not exist in Workflow"):
            workflow_orchestrator.search(clean_db, {'invalid_field': 'value'})

@pytest.mark.integration
class TestWorkflowOrchestrationGet:
    def test_get_workflow_with_valid_id(self, clean_db, workflow_orchestrator, sample_workflow_data):
        # Create a workflow first
        workflow = workflow_orchestrator.create(clean_db, sample_workflow_data)
        
        # Get workflow without details
        result = workflow_orchestrator.get(clean_db, workflow['id'], include_details=False)
        
        assert result is not None
        assert result['id'] == workflow['id']
        assert result['name'] == sample_workflow_data['name']
        assert result['description'] == sample_workflow_data['description']
        assert result['priority'] == sample_workflow_data['priority']
        assert 'node_count' in result
        assert 'edge_count' in result
        assert result['node_count'] == 0  # No nodes created yet
        assert result['edge_count'] == 0  # No edges created yet
        # Should not have detailed nodes/edges
        assert 'nodes' not in result
        assert 'edges' not in result

    def test_get_workflow_with_invalid_id(self, clean_db, workflow_orchestrator):
        # Try to get workflow with invalid ID
        with pytest.raises(BusinessLogicError, match="Workflow not found: WF-INVALID"):
            workflow_orchestrator.get(clean_db, 'WF-INVALID', include_details=False)

    def test_get_workflow_with_include_details(self, clean_db, workflow_orchestrator, sample_workflow_data):
        # Create a workflow first
        workflow = workflow_orchestrator.create(clean_db, sample_workflow_data)
        
        # Get workflow with details
        result = workflow_orchestrator.get(clean_db, workflow['id'], include_details=True)
        
        assert result is not None
        assert result['id'] == workflow['id']
        assert result['name'] == sample_workflow_data['name']
        assert 'node_count' in result
        assert 'edge_count' in result
        assert result['node_count'] == 0  # No nodes created yet
        assert result['edge_count'] == 0  # No edges created yet
        # Should have detailed nodes/edges (empty lists)
        assert 'nodes' in result
        assert 'edges' in result
        assert isinstance(result['nodes'], list)
        assert isinstance(result['edges'], list)
        assert len(result['nodes']) == 0
        assert len(result['edges']) == 0

@pytest.mark.integration
class TestWorkflowOrchestrationExtraOperations:
    def test_count_workflow(self, clean_db, workflow_orchestrator, sample_workflow_data_batch):
        # Initially should be 0
        initial_count = workflow_orchestrator.count(clean_db)
        assert initial_count == 0
        
        # Create multiple workflows
        for workflow_data in sample_workflow_data_batch:
            workflow_orchestrator.create(clean_db, workflow_data)
        
        # Count should match number of created workflows
        final_count = workflow_orchestrator.count(clean_db)
        assert final_count == len(sample_workflow_data_batch)

    def test_exists_workflow_with_valid_id(self, clean_db, workflow_orchestrator, sample_workflow_data):
        # Create a workflow
        workflow = workflow_orchestrator.create(clean_db, sample_workflow_data)
        
        # Check if workflow exists
        exists = workflow_orchestrator.exists(clean_db, workflow['id'])
        assert exists is True

    def test_exists_workflow_with_invalid_id(self, clean_db, workflow_orchestrator):
        # Check if non-existent workflow exists
        exists = workflow_orchestrator.exists(clean_db, 'WF-NONEXISTENT')
        assert exists is False

    def test_set_status_active(self, clean_db, workflow_orchestrator, sample_workflow_data):
        # Create a workflow (default status is DRAFT)
        workflow = workflow_orchestrator.create(clean_db, sample_workflow_data)
        assert workflow['status'] == WorkflowStatus.DRAFT
        
        # Set status to ACTIVE
        updated_workflow = workflow_orchestrator.set_status_active(clean_db, workflow['id'])
        
        assert updated_workflow is not None
        assert updated_workflow['id'] == workflow['id']
        assert updated_workflow['status'] == WorkflowStatus.ACTIVE
        
        # Verify in database
        db_workflow = clean_db.get(Workflow, workflow['id'])
        assert db_workflow.status == WorkflowStatus.ACTIVE

    def test_set_status_draft(self, clean_db, workflow_orchestrator, sample_workflow_data):
        # Create a workflow and set it to ACTIVE first
        workflow = workflow_orchestrator.create(clean_db, sample_workflow_data)
        workflow_orchestrator.set_status_active(clean_db, workflow['id'])
        
        # Set status back to DRAFT
        updated_workflow = workflow_orchestrator.set_status_draft(clean_db, workflow['id'])
        
        assert updated_workflow is not None
        assert updated_workflow['id'] == workflow['id']
        assert updated_workflow['status'] == WorkflowStatus.DRAFT
        
        # Verify in database
        db_workflow = clean_db.get(Workflow, workflow['id'])
        assert db_workflow.status == WorkflowStatus.DRAFT

    def test_get_active_workflows(self, clean_db, workflow_orchestrator, sample_workflow_data_batch):
        # Create workflows with mixed statuses
        created_workflows = []
        for workflow_data in sample_workflow_data_batch:
            workflow = workflow_orchestrator.create(clean_db, workflow_data)
            created_workflows.append(workflow)
        
        # Set some workflows to ACTIVE
        workflow_orchestrator.set_status_active(clean_db, created_workflows[0]['id'])
        workflow_orchestrator.set_status_active(clean_db, created_workflows[2]['id'])
        # created_workflows[1] remains DRAFT
        
        # Get active workflows
        active_workflows = workflow_orchestrator.get_active_workflows(clean_db)
        
        assert len(active_workflows) == 2
        active_ids = [wf['id'] for wf in active_workflows]
        assert created_workflows[0]['id'] in active_ids
        assert created_workflows[2]['id'] in active_ids
        assert created_workflows[1]['id'] not in active_ids

    def test_get_draft_workflows(self, clean_db, workflow_orchestrator, sample_workflow_data_batch):
        # Create workflows with mixed statuses
        created_workflows = []
        for workflow_data in sample_workflow_data_batch:
            workflow = workflow_orchestrator.create(clean_db, workflow_data)
            created_workflows.append(workflow)
        
        # Set some workflows to ACTIVE
        workflow_orchestrator.set_status_active(clean_db, created_workflows[0]['id'])
        # created_workflows[1] and created_workflows[2] remain DRAFT
        
        # Get draft workflows
        draft_workflows = workflow_orchestrator.get_draft_workflows(clean_db)
        
        assert len(draft_workflows) == 2
        draft_ids = [wf['id'] for wf in draft_workflows]
        assert created_workflows[1]['id'] in draft_ids
        assert created_workflows[2]['id'] in draft_ids
        assert created_workflows[0]['id'] not in draft_ids

    def test_set_priority(self, clean_db, workflow_orchestrator, sample_workflow_data):
        # Create a workflow
        workflow = workflow_orchestrator.create(clean_db, sample_workflow_data)
        assert workflow['priority'] == 5  # Initial priority from sample data
        
        # Set new priority
        new_priority = 8
        updated_workflow = workflow_orchestrator.set_priority(clean_db, workflow['id'], new_priority)
        
        assert updated_workflow is not None
        assert updated_workflow['id'] == workflow['id']
        assert updated_workflow['priority'] == new_priority
        
        # Verify in database
        db_workflow = clean_db.get(Workflow, workflow['id'])
        assert db_workflow.priority == new_priority
    
    def test_set_priority_with_invalid_range(self, clean_db, workflow_orchestrator, sample_workflow_data):
        # Create a workflow
        workflow = workflow_orchestrator.create(clean_db, sample_workflow_data)
        
        # Test invalid priority values
        with pytest.raises(ValidationError, match="Priority must be an integer between 0 and 10"):
            workflow_orchestrator.set_priority(clean_db, workflow['id'], -1)
        
        with pytest.raises(ValidationError, match="Priority must be an integer between 0 and 10"):
            workflow_orchestrator.set_priority(clean_db, workflow['id'], 11)
        
        with pytest.raises(ValidationError, match="Priority must be an integer between 0 and 10"):
            workflow_orchestrator.set_priority(clean_db, workflow['id'], "invalid")
    
    def test_set_priority_with_invalid_workflow_id(self, clean_db, workflow_orchestrator):
        # Test with non-existent workflow ID
        with pytest.raises(BusinessLogicError, match="Workflow not found: WF-INVALID"):
            workflow_orchestrator.set_priority(clean_db, 'WF-INVALID', 5)