import pytest
import os
from sqlalchemy.orm import Session

from miniflow.database.orchestration.node_orchestrator import NodeOrchestrator
from miniflow.database.orchestration.workflow_orchestration import WorkflowOrchestrator
from miniflow.database.orchestration.script_orchestration import ScriptOrchestrator
from miniflow.database.orchestration.edge_orchestrator import EdgeOrchestrator
from miniflow.database.models import Node, Workflow, Script, Edge, WorkflowStatus, ScriptType, ScriptTestStatus
from miniflow.exceptions import ValidationError, BusinessLogicError, ResourceError


@pytest.fixture
def node_orchestrator():
    return NodeOrchestrator()


@pytest.fixture
def workflow_orchestrator():
    return WorkflowOrchestrator()


@pytest.fixture
def script_orchestrator():
    return ScriptOrchestrator()


@pytest.fixture
def edge_orchestrator():
    return EdgeOrchestrator()


@pytest.fixture
def sample_workflow_data():
    return {
        'name': 'test_workflow',
        'description': 'Integration test workflow',
        'status': WorkflowStatus.DRAFT,
        'priority': 5
    }


@pytest.fixture
def sample_script_data():
    return {
        'name': 'test_script',
        'description': 'Integration test script',
        'language': ScriptType.PYTHON,
        'script_content': 'print("Hello World")',
        'input_params': {'param1': 'string', 'param2': 'int'},
        'output_params': {'result': 'string'},
        'test_status': ScriptTestStatus.UNTESTED
    }


@pytest.fixture
def sample_node_data():
    return {
        'name': 'test_node',
        'description': 'Integration test node',
        'params': {'batch_size': 100, 'timeout': 30},
        'max_retries': 3,
        'timeout_seconds': 300
    }


@pytest.fixture
def temp_script_path(tmp_path):
    """Create a temporary directory for script files"""
    script_dir = tmp_path / "scripts"
    script_dir.mkdir()
    return str(script_dir)


@pytest.fixture
def setup_workflow_and_script(clean_db, workflow_orchestrator, script_orchestrator, temp_script_path, sample_workflow_data, sample_script_data):
    """Setup workflow and script for node tests"""
    workflow = workflow_orchestrator.create(clean_db, sample_workflow_data)
    script = script_orchestrator.create(clean_db, temp_script_path, sample_script_data)
    return workflow, script


@pytest.mark.integration
class TestNodeOrchestrationCreate:
    def test_create_node_with_valid_data(self, clean_db, node_orchestrator, setup_workflow_and_script, sample_node_data):
        workflow, script = setup_workflow_and_script
        node_data = sample_node_data.copy()
        node_data['workflow_id'] = workflow['id']
        node_data['script_id'] = script['id']
        
        result = node_orchestrator.create(clean_db, node_data)
        
        assert result is not None
        assert result['name'] == 'test_node'
        assert result['workflow_id'] == workflow['id']
        assert result['script_id'] == script['id']
        assert result['description'] == 'Integration test node'

    def test_create_node_without_script(self, clean_db, node_orchestrator, setup_workflow_and_script, sample_node_data):
        workflow, _ = setup_workflow_and_script
        node_data = sample_node_data.copy()
        node_data['workflow_id'] = workflow['id']
        # Don't set script_id - should be allowed (nullable)
        
        result = node_orchestrator.create(clean_db, node_data)
        
        assert result is not None
        assert result['name'] == 'test_node'
        assert result['workflow_id'] == workflow['id']
        assert result.get('script_id') is None

    def test_create_node_with_missing_workflow_id(self, clean_db, node_orchestrator, sample_node_data):
        with pytest.raises(ValidationError, match="Workflow ID is required"):
            node_orchestrator.create(clean_db, sample_node_data)

    def test_create_node_with_invalid_workflow_id(self, clean_db, node_orchestrator, sample_node_data):
        node_data = sample_node_data.copy()
        node_data['workflow_id'] = 'WF-INVALID'
        
        with pytest.raises(BusinessLogicError, match="Workflow not found: WF-INVALID"):
            node_orchestrator.create(clean_db, node_data)

    def test_create_node_with_invalid_script_id(self, clean_db, node_orchestrator, setup_workflow_and_script, sample_node_data):
        workflow, _ = setup_workflow_and_script
        node_data = sample_node_data.copy()
        node_data['workflow_id'] = workflow['id']
        node_data['script_id'] = 'SC-INVALID'
        
        with pytest.raises(BusinessLogicError, match="Script not found: SC-INVALID"):
            node_orchestrator.create(clean_db, node_data)

    def test_create_node_with_missing_name(self, clean_db, node_orchestrator, setup_workflow_and_script, sample_node_data):
        workflow, _ = setup_workflow_and_script
        node_data = sample_node_data.copy()
        node_data['workflow_id'] = workflow['id']
        del node_data['name']
        
        with pytest.raises(ValidationError, match="Node name is required"):
            node_orchestrator.create(clean_db, node_data)

    def test_create_node_with_invalid_name(self, clean_db, node_orchestrator, setup_workflow_and_script, sample_node_data):
        workflow, _ = setup_workflow_and_script
        node_data = sample_node_data.copy()
        node_data['workflow_id'] = workflow['id']
        node_data['name'] = 'invalid@name!'
        
        with pytest.raises(ValidationError, match="Node name must contain only alphanumeric characters"):
            node_orchestrator.create(clean_db, node_data)

    def test_create_node_with_duplicate_name_in_workflow(self, clean_db, node_orchestrator, setup_workflow_and_script, sample_node_data):
        workflow, _ = setup_workflow_and_script
        node_data = sample_node_data.copy()
        node_data['workflow_id'] = workflow['id']
        
        # Create first node
        node_orchestrator.create(clean_db, node_data)
        
        # Try to create second node with same name in same workflow
        with pytest.raises(ValidationError, match="Node with name 'test_node' already exists in workflow"):
            node_orchestrator.create(clean_db, node_data)


@pytest.mark.integration
class TestNodeOrchestrationUpdate:
    def test_update_node_with_valid_data(self, clean_db, node_orchestrator, setup_workflow_and_script, sample_node_data):
        workflow, script = setup_workflow_and_script
        node_data = sample_node_data.copy()
        node_data['workflow_id'] = workflow['id']
        node_data['script_id'] = script['id']
        
        # Create node
        node = node_orchestrator.create(clean_db, node_data)
        
        # Update node
        update_data = {
            'description': 'Updated description',
            'max_retries': 5,
            'params': {'new_param': 'value'}
        }
        updated_node = node_orchestrator.update(clean_db, node['id'], update_data)
        
        assert updated_node['description'] == 'Updated description'
        assert updated_node['max_retries'] == 5
        assert updated_node['params'] == {'new_param': 'value'}

    def test_update_node_with_new_name(self, clean_db, node_orchestrator, setup_workflow_and_script, sample_node_data):
        workflow, _ = setup_workflow_and_script
        node_data = sample_node_data.copy()
        node_data['workflow_id'] = workflow['id']
        
        # Create node
        node = node_orchestrator.create(clean_db, node_data)
        
        # Update name
        update_data = {'name': 'updated_node_name'}
        updated_node = node_orchestrator.update(clean_db, node['id'], update_data)
        
        assert updated_node['name'] == 'updated_node_name'

    def test_update_node_with_invalid_id(self, clean_db, node_orchestrator):
        with pytest.raises(BusinessLogicError, match="Node not found: ND-INVALID"):
            node_orchestrator.update(clean_db, 'ND-INVALID', {'description': 'test'})

    def test_update_node_with_invalid_workflow_id(self, clean_db, node_orchestrator, setup_workflow_and_script, sample_node_data):
        workflow, _ = setup_workflow_and_script
        node_data = sample_node_data.copy()
        node_data['workflow_id'] = workflow['id']
        
        # Create node
        node = node_orchestrator.create(clean_db, node_data)
        
        # Try to update with invalid workflow
        with pytest.raises(BusinessLogicError, match="Workflow not found: WF-INVALID"):
            node_orchestrator.update(clean_db, node['id'], {'workflow_id': 'WF-INVALID'})

    def test_update_node_with_invalid_script_id(self, clean_db, node_orchestrator, setup_workflow_and_script, sample_node_data):
        workflow, _ = setup_workflow_and_script
        node_data = sample_node_data.copy()
        node_data['workflow_id'] = workflow['id']
        
        # Create node
        node = node_orchestrator.create(clean_db, node_data)
        
        # Try to update with invalid script
        with pytest.raises(BusinessLogicError, match="Script not found: SC-INVALID"):
            node_orchestrator.update(clean_db, node['id'], {'script_id': 'SC-INVALID'})

    def test_update_node_with_duplicate_name(self, clean_db, node_orchestrator, setup_workflow_and_script, sample_node_data):
        workflow, _ = setup_workflow_and_script
        node_data1 = sample_node_data.copy()
        node_data1['workflow_id'] = workflow['id']
        node_data1['name'] = 'node1'
        
        node_data2 = sample_node_data.copy()
        node_data2['workflow_id'] = workflow['id']
        node_data2['name'] = 'node2'
        
        # Create two nodes
        node1 = node_orchestrator.create(clean_db, node_data1)
        node2 = node_orchestrator.create(clean_db, node_data2)
        
        # Try to rename node2 to node1's name
        with pytest.raises(ValidationError, match="Node with name 'node1' already exists in workflow"):
            node_orchestrator.update(clean_db, node2['id'], {'name': 'node1'})

    def test_update_node_with_invalid_name(self, clean_db, node_orchestrator, setup_workflow_and_script, sample_node_data):
        workflow, _ = setup_workflow_and_script
        node_data = sample_node_data.copy()
        node_data['workflow_id'] = workflow['id']
        
        # Create node
        node = node_orchestrator.create(clean_db, node_data)
        
        # Try to update with invalid name
        with pytest.raises(ValidationError, match="Node name must contain only alphanumeric characters"):
            node_orchestrator.update(clean_db, node['id'], {'name': 'invalid@name!'})


@pytest.mark.integration
class TestNodeOrchestrationDelete:
    def test_delete_node_with_valid_id(self, clean_db, node_orchestrator, setup_workflow_and_script, sample_node_data):
        workflow, _ = setup_workflow_and_script
        node_data = sample_node_data.copy()
        node_data['workflow_id'] = workflow['id']
        
        # Create node
        node = node_orchestrator.create(clean_db, node_data)
        
        # Delete node
        result = node_orchestrator.delete(clean_db, node['id'])
        
        assert result is not None
        assert result['id'] == node['id']
        
        # Verify node was deleted
        db_node = clean_db.get(Node, node['id'])
        assert db_node is None

    def test_delete_node_with_invalid_id(self, clean_db, node_orchestrator):
        with pytest.raises(BusinessLogicError, match="Node not found: ND-INVALID"):
            node_orchestrator.delete(clean_db, 'ND-INVALID')

    def test_delete_node_with_dependencies_without_force(self, clean_db, node_orchestrator, edge_orchestrator, setup_workflow_and_script, sample_node_data):
        workflow, _ = setup_workflow_and_script
        
        # Create two nodes
        node_data1 = sample_node_data.copy()
        node_data1['workflow_id'] = workflow['id']
        node_data1['name'] = 'node1'
        node1 = node_orchestrator.create(clean_db, node_data1)
        
        node_data2 = sample_node_data.copy()
        node_data2['workflow_id'] = workflow['id']
        node_data2['name'] = 'node2'
        node2 = node_orchestrator.create(clean_db, node_data2)
        
        # Create edge between them
        edge_data = {
            'workflow_id': workflow['id'],
            'from_node_id': node1['id'],
            'to_node_id': node2['id']
        }
        edge_orchestrator.create(clean_db, edge_data)
        
        # Try to delete node1 without force - should fail due to outgoing dependency
        with pytest.raises(BusinessLogicError, match="Cannot delete node 'node1' - it has 1 outgoing dependencies"):
            node_orchestrator.delete(clean_db, node1['id'])

    def test_delete_node_with_dependencies_with_force(self, clean_db, node_orchestrator, edge_orchestrator, setup_workflow_and_script, sample_node_data):
        workflow, _ = setup_workflow_and_script
        
        # Create two nodes
        node_data1 = sample_node_data.copy()
        node_data1['workflow_id'] = workflow['id']
        node_data1['name'] = 'node1'
        node1 = node_orchestrator.create(clean_db, node_data1)
        
        node_data2 = sample_node_data.copy()
        node_data2['workflow_id'] = workflow['id']
        node_data2['name'] = 'node2'
        node2 = node_orchestrator.create(clean_db, node_data2)
        
        # Create edge between them
        edge_data = {
            'workflow_id': workflow['id'],
            'from_node_id': node1['id'],
            'to_node_id': node2['id']
        }
        edge = edge_orchestrator.create(clean_db, edge_data)
        
        # Delete node1 with force - should succeed and delete edge
        result = node_orchestrator.delete(clean_db, node1['id'], force=True)
        
        assert result is not None
        assert result['id'] == node1['id']
        
        # Verify node was deleted
        db_node = clean_db.get(Node, node1['id'])
        assert db_node is None
        
        # Verify edge was also deleted
        db_edge = clean_db.get(Edge, edge['id'])
        assert db_edge is None


@pytest.mark.integration
class TestNodeOrchestrationGet:
    def test_get_node_with_valid_id(self, clean_db, node_orchestrator, setup_workflow_and_script, sample_node_data):
        workflow, script = setup_workflow_and_script
        node_data = sample_node_data.copy()
        node_data['workflow_id'] = workflow['id']
        node_data['script_id'] = script['id']
        
        # Create node
        node = node_orchestrator.create(clean_db, node_data)
        
        # Get node
        result = node_orchestrator.get(clean_db, node['id'])
        
        assert result is not None
        assert result['id'] == node['id']
        assert result['name'] == 'test_node'
        assert result['workflow_id'] == workflow['id']
        assert result['script_id'] == script['id']

    def test_get_node_with_details(self, clean_db, node_orchestrator, setup_workflow_and_script, sample_node_data):
        workflow, script = setup_workflow_and_script
        node_data = sample_node_data.copy()
        node_data['workflow_id'] = workflow['id']
        node_data['script_id'] = script['id']
        
        # Create node
        node = node_orchestrator.create(clean_db, node_data)
        
        # Get node with details
        result = node_orchestrator.get(clean_db, node['id'], include_details=True)
        
        assert result is not None
        assert result['id'] == node['id']
        # Check enhanced details
        assert result['workflow_name'] == workflow['name']
        assert result['script_name'] == script['name']
        assert result['script_input_params'] == script['input_params']
        assert result['script_output_params'] == script['output_params']
        assert result['script_language'] == script['language']
        assert result['script_test_status'] == script['test_status']
        assert 'incoming_dependencies' in result
        assert 'outgoing_dependencies' in result
        assert 'has_self_dependency' in result

    def test_get_node_without_script_with_details(self, clean_db, node_orchestrator, setup_workflow_and_script, sample_node_data):
        workflow, _ = setup_workflow_and_script
        node_data = sample_node_data.copy()
        node_data['workflow_id'] = workflow['id']
        # No script_id
        
        # Create node
        node = node_orchestrator.create(clean_db, node_data)
        
        # Get node with details
        result = node_orchestrator.get(clean_db, node['id'], include_details=True)
        
        assert result is not None
        assert result['workflow_name'] == workflow['name']
        assert result['script_name'] is None
        assert result['script_input_params'] is None
        assert result['script_output_params'] is None
        assert result['script_language'] is None
        assert result['script_test_status'] is None

    def test_get_node_with_invalid_id(self, clean_db, node_orchestrator):
        with pytest.raises(BusinessLogicError, match="Node not found: ND-INVALID"):
            node_orchestrator.get(clean_db, 'ND-INVALID')


@pytest.mark.integration
class TestNodeOrchestrationSearch:
    def test_search_node_with_one_criteria(self, clean_db, node_orchestrator, setup_workflow_and_script, sample_node_data):
        workflow, _ = setup_workflow_and_script
        node_data = sample_node_data.copy()
        node_data['workflow_id'] = workflow['id']
        
        # Create node
        node = node_orchestrator.create(clean_db, node_data)
        
        # Search by workflow_id
        result = node_orchestrator.search(clean_db, {'workflow_id': workflow['id']})
        
        assert result['total_count'] >= 1
        assert len(result['data']) >= 1
        assert any(n['id'] == node['id'] for n in result['data'])

    def test_search_node_with_invalid_criteria(self, clean_db, node_orchestrator):
        result = node_orchestrator.search(clean_db, {'workflow_id': 'WF-INVALID'})
        
        assert result['total_count'] == 0
        assert len(result['data']) == 0


@pytest.mark.integration
class TestNodeOrchestrationExtraOperations:
    def test_count_nodes(self, clean_db, node_orchestrator, setup_workflow_and_script, sample_node_data):
        workflow, _ = setup_workflow_and_script
        
        # Get initial count
        initial_count = node_orchestrator.count(clean_db)
        
        # Create node
        node_data = sample_node_data.copy()
        node_data['workflow_id'] = workflow['id']
        node_orchestrator.create(clean_db, node_data)
        
        # Check count increased
        new_count = node_orchestrator.count(clean_db)
        assert new_count == initial_count + 1

    def test_count_nodes_by_workflow(self, clean_db, node_orchestrator, setup_workflow_and_script, sample_node_data):
        workflow, _ = setup_workflow_and_script
        
        # Create node
        node_data = sample_node_data.copy()
        node_data['workflow_id'] = workflow['id']
        node_orchestrator.create(clean_db, node_data)
        
        # Count nodes in this workflow
        count = node_orchestrator.count(clean_db, workflow_id=workflow['id'])
        assert count >= 1

    def test_exists_node_with_valid_id(self, clean_db, node_orchestrator, setup_workflow_and_script, sample_node_data):
        workflow, _ = setup_workflow_and_script
        node_data = sample_node_data.copy()
        node_data['workflow_id'] = workflow['id']
        
        # Create node
        node = node_orchestrator.create(clean_db, node_data)
        
        # Check exists
        assert node_orchestrator.exists(clean_db, node['id']) is True

    def test_exists_node_with_invalid_id(self, clean_db, node_orchestrator):
        assert node_orchestrator.exists(clean_db, 'ND-INVALID') is False

    def test_get_all_nodes(self, clean_db, node_orchestrator, setup_workflow_and_script, sample_node_data):
        workflow, _ = setup_workflow_and_script
        node_data = sample_node_data.copy()
        node_data['workflow_id'] = workflow['id']
        
        # Create node
        node = node_orchestrator.create(clean_db, node_data)
        
        # Get all nodes
        nodes = node_orchestrator.get_all(clean_db)
        
        assert len(nodes) >= 1
        assert any(n['id'] == node['id'] for n in nodes)

    def test_get_by_workflow(self, clean_db, node_orchestrator, setup_workflow_and_script, sample_node_data):
        workflow, _ = setup_workflow_and_script
        node_data = sample_node_data.copy()
        node_data['workflow_id'] = workflow['id']
        
        # Create node
        node = node_orchestrator.create(clean_db, node_data)
        
        # Get nodes by workflow
        nodes = node_orchestrator.get_by_workflow(clean_db, workflow['id'])
        
        assert len(nodes) >= 1
        assert any(n['id'] == node['id'] for n in nodes)

    def test_get_by_workflow_with_invalid_id(self, clean_db, node_orchestrator):
        with pytest.raises(BusinessLogicError, match="Workflow not found: WF-INVALID"):
            node_orchestrator.get_by_workflow(clean_db, 'WF-INVALID')

    def test_get_by_script(self, clean_db, node_orchestrator, setup_workflow_and_script, sample_node_data):
        workflow, script = setup_workflow_and_script
        node_data = sample_node_data.copy()
        node_data['workflow_id'] = workflow['id']
        node_data['script_id'] = script['id']
        
        # Create node
        node = node_orchestrator.create(clean_db, node_data)
        
        # Get nodes by script
        nodes = node_orchestrator.get_by_script(clean_db, script['id'])
        
        assert len(nodes) >= 1
        assert any(n['id'] == node['id'] for n in nodes)

    def test_get_by_script_with_invalid_id(self, clean_db, node_orchestrator):
        with pytest.raises(BusinessLogicError, match="Script not found: SC-INVALID"):
            node_orchestrator.get_by_script(clean_db, 'SC-INVALID')

    def test_search_nodes_all(self, clean_db, node_orchestrator, setup_workflow_and_script, sample_node_data):
        workflow, _ = setup_workflow_and_script
        node_data = sample_node_data.copy()
        node_data['workflow_id'] = workflow['id']
        
        # Create node
        node = node_orchestrator.create(clean_db, node_data)
        
        # Search all nodes (empty criteria)
        result = node_orchestrator.search(clean_db, {})
        
        assert 'data' in result
        assert 'total_count' in result
        assert len(result['data']) >= 1

    def test_search_nodes_by_workflow(self, clean_db, node_orchestrator, setup_workflow_and_script, sample_node_data):
        workflow, _ = setup_workflow_and_script
        node_data = sample_node_data.copy()
        node_data['workflow_id'] = workflow['id']
        
        # Create node
        node = node_orchestrator.create(clean_db, node_data)
        
        # Search nodes by workflow
        result = node_orchestrator.search(clean_db, {'workflow_id': workflow['id']})
        
        assert 'data' in result
        assert 'total_count' in result
        assert any(n['id'] == node['id'] for n in result['data'])