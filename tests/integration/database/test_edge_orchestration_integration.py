# tests/integration/database/test_edge_orchestration_integration.py
import pytest
import os
from sqlalchemy.orm import Session

from miniflow.database.orchestration.edge_orchestrator import EdgeOrchestrator
from miniflow.database.orchestration.workflow_orchestration import WorkflowOrchestrator
from miniflow.database.orchestration.node_orchestrator import NodeOrchestrator
from miniflow.database.orchestration.script_orchestration import ScriptOrchestrator
from miniflow.database.models import Edge, Node, Workflow, Script
from miniflow.exceptions import ValidationError, BusinessLogicError


@pytest.fixture
def edge_orchestrator():
    return EdgeOrchestrator()


@pytest.fixture
def workflow_orchestrator():
    return WorkflowOrchestrator()


@pytest.fixture
def node_orchestrator():
    return NodeOrchestrator()


@pytest.fixture
def script_orchestrator():
    return ScriptOrchestrator()


@pytest.fixture
def setup_workflow_and_nodes(clean_db, workflow_orchestrator, node_orchestrator):
    """Setup workflow with two nodes for edge creation"""
    # Create workflow
    workflow_data = {
        'name': 'Edge Test Workflow',
        'description': 'Integration test workflow for edges',
        'priority': 5
    }
    workflow = workflow_orchestrator.create(clean_db, workflow_data)
    
    # Create first node
    node_data1 = {
        'workflow_id': workflow['id'],
        'name': 'source_node',
        'description': 'Source node for edge testing',
        'max_retries': 3,
        'params': {'batch_size': 100, 'timeout': 30}
    }
    node1 = node_orchestrator.create(clean_db, node_data1)
    
    # Create second node
    node_data2 = {
        'workflow_id': workflow['id'],
        'name': 'target_node',
        'description': 'Target node for edge testing',
        'max_retries': 2,
        'params': {'output_format': 'json'}
    }
    node2 = node_orchestrator.create(clean_db, node_data2)
    
    return workflow, node1, node2


@pytest.fixture
def sample_edge_data(setup_workflow_and_nodes):
    """Sample edge data for testing"""
    workflow, node1, node2 = setup_workflow_and_nodes
    return {
        'workflow_id': workflow['id'],
        'from_node_id': node1['id'],
        'to_node_id': node2['id'],
        'condition_type': 'success',
        'condition_params': {'exit_code': 0}
    }


@pytest.mark.integration
class TestEdgeOrchestrationCreate:
    def test_create_edge_with_valid_data(self, clean_db, edge_orchestrator, sample_edge_data):
        # Create edge
        result = edge_orchestrator.create(clean_db, sample_edge_data)
        
        # Verify response structure
        assert result is not None
        assert 'id' in result
        assert result['workflow_id'] == sample_edge_data['workflow_id']
        assert result['from_node_id'] == sample_edge_data['from_node_id']
        assert result['to_node_id'] == sample_edge_data['to_node_id']
        assert result['condition_type'] == sample_edge_data['condition_type']
        
        # Verify in database
        db_edge = clean_db.get(Edge, result['id'])
        assert db_edge is not None
        assert db_edge.workflow_id == sample_edge_data['workflow_id']
        assert db_edge.from_node_id == sample_edge_data['from_node_id']
        assert db_edge.to_node_id == sample_edge_data['to_node_id']

    def test_create_edge_with_missing_from_node_id(self, clean_db, edge_orchestrator, sample_edge_data):
        # Remove from_node_id
        del sample_edge_data['from_node_id']
        
        # Attempt to create edge
        with pytest.raises(ValidationError) as exc_info:
            edge_orchestrator.create(clean_db, sample_edge_data)
        
        assert "From node ID is required" in str(exc_info.value)

    def test_create_edge_with_missing_to_node_id(self, clean_db, edge_orchestrator, sample_edge_data):
        # Remove to_node_id
        del sample_edge_data['to_node_id']
        
        # Attempt to create edge
        with pytest.raises(ValidationError) as exc_info:
            edge_orchestrator.create(clean_db, sample_edge_data)
        
        assert "To node ID is required" in str(exc_info.value)

    def test_create_edge_with_invalid_from_node_id(self, clean_db, edge_orchestrator, sample_edge_data):
        # Set invalid from_node_id
        sample_edge_data['from_node_id'] = 'INVALID-NODE-ID'
        
        # Attempt to create edge
        with pytest.raises(BusinessLogicError) as exc_info:
            edge_orchestrator.create(clean_db, sample_edge_data)
        
        assert "From node not found" in str(exc_info.value)

    def test_create_edge_with_invalid_to_node_id(self, clean_db, edge_orchestrator, sample_edge_data):
        # Set invalid to_node_id
        sample_edge_data['to_node_id'] = 'INVALID-NODE-ID'
        
        # Attempt to create edge
        with pytest.raises(BusinessLogicError) as exc_info:
            edge_orchestrator.create(clean_db, sample_edge_data)
        
        assert "To node not found" in str(exc_info.value)

    def test_create_edge_with_self_loop(self, clean_db, edge_orchestrator, sample_edge_data):
        # Set same node for from and to
        sample_edge_data['to_node_id'] = sample_edge_data['from_node_id']
        
        # Attempt to create edge
        with pytest.raises(ValidationError) as exc_info:
            edge_orchestrator.create(clean_db, sample_edge_data)
        
        assert "Self-loops are not allowed" in str(exc_info.value)

    def test_create_edge_with_nodes_in_different_workflows(self, clean_db, edge_orchestrator, workflow_orchestrator, node_orchestrator, sample_edge_data):
        # Create another workflow
        workflow_data2 = {
            'name': 'Different Workflow',
            'description': 'Another workflow for testing',
            'priority': 3
        }
        workflow2 = workflow_orchestrator.create(clean_db, workflow_data2)
        
        # Create node in different workflow
        node_data3 = {
            'workflow_id': workflow2['id'],
            'name': 'different_workflow_node',
            'description': 'Node in different workflow',
            'max_retries': 1,
            'params': {}
        }
        node3 = node_orchestrator.create(clean_db, node_data3)
        
        # Try to create edge between nodes in different workflows
        sample_edge_data['to_node_id'] = node3['id']
        
        with pytest.raises(ValidationError) as exc_info:
            edge_orchestrator.create(clean_db, sample_edge_data)
        
        assert "Nodes must be in the same workflow" in str(exc_info.value)

    def test_create_duplicate_edge(self, clean_db, edge_orchestrator, sample_edge_data):
        # Create first edge
        edge1 = edge_orchestrator.create(clean_db, sample_edge_data)
        assert edge1 is not None
        
        # Attempt to create duplicate edge
        with pytest.raises(ValidationError) as exc_info:
            edge_orchestrator.create(clean_db, sample_edge_data)
        
        assert "Edge already exists between nodes" in str(exc_info.value)

    def test_create_edge_without_condition(self, clean_db, edge_orchestrator, sample_edge_data):
        # Remove condition fields
        del sample_edge_data['condition_type']
        del sample_edge_data['condition_params']
        
        # Create edge
        result = edge_orchestrator.create(clean_db, sample_edge_data)
        
        # Verify response (Edge model has default ConditionType.SUCCESS)
        assert result is not None
        assert result['condition_type'] == 'success'  # Default value from enum
        
        # Verify in database
        db_edge = clean_db.get(Edge, result['id'])
        assert db_edge.condition_type.value == 'success'


@pytest.mark.integration
class TestEdgeOrchestrationUpdate:
    def test_update_edge_with_valid_data(self, clean_db, edge_orchestrator, sample_edge_data):
        # Create edge
        edge = edge_orchestrator.create(clean_db, sample_edge_data)
        
        # Update edge
        update_data = {
            'condition_type': 'failure',  # Use lowercase as defined in enum
            'condition_params': {'exit_code': 1}
        }
        result = edge_orchestrator.update(clean_db, edge['id'], update_data)
        
        # Verify response
        assert result is not None
        assert result['id'] == edge['id']
        assert result['condition_type'] == 'failure'
        
        # Verify in database
        db_edge = clean_db.get(Edge, edge['id'])
        assert db_edge.condition_type.value == 'failure'

    def test_update_edge_with_invalid_id(self, clean_db, edge_orchestrator):
        # Attempt to update non-existent edge
        update_data = {'condition_type': 'SUCCESS'}
        
        with pytest.raises(BusinessLogicError) as exc_info:
            edge_orchestrator.update(clean_db, 'INVALID-EDGE-ID', update_data)
        
        assert "Edge not found" in str(exc_info.value)

    def test_update_edge_with_new_nodes(self, clean_db, edge_orchestrator, sample_edge_data, node_orchestrator):
        # Create edge
        edge = edge_orchestrator.create(clean_db, sample_edge_data)
        
        # Create third node
        node_data3 = {
            'workflow_id': sample_edge_data['workflow_id'],
            'name': 'third_node',
            'description': 'Third node for testing',
            'max_retries': 1,
            'params': {}
        }
        node3 = node_orchestrator.create(clean_db, node_data3)
        
        # Update edge to point to new node
        update_data = {'to_node_id': node3['id']}
        result = edge_orchestrator.update(clean_db, edge['id'], update_data)
        
        # Verify response
        assert result is not None
        assert result['to_node_id'] == node3['id']
        
        # Verify in database
        db_edge = clean_db.get(Edge, edge['id'])
        assert db_edge.to_node_id == node3['id']

    def test_update_edge_with_invalid_from_node_id(self, clean_db, edge_orchestrator, sample_edge_data):
        # Create edge
        edge = edge_orchestrator.create(clean_db, sample_edge_data)
        
        # Update with invalid from_node_id
        update_data = {'from_node_id': 'INVALID-NODE-ID'}
        
        with pytest.raises(BusinessLogicError) as exc_info:
            edge_orchestrator.update(clean_db, edge['id'], update_data)
        
        assert "From node not found" in str(exc_info.value)

    def test_update_edge_with_invalid_to_node_id(self, clean_db, edge_orchestrator, sample_edge_data):
        # Create edge
        edge = edge_orchestrator.create(clean_db, sample_edge_data)
        
        # Update with invalid to_node_id
        update_data = {'to_node_id': 'INVALID-NODE-ID'}
        
        with pytest.raises(BusinessLogicError) as exc_info:
            edge_orchestrator.update(clean_db, edge['id'], update_data)
        
        assert "To node not found" in str(exc_info.value)

    def test_update_edge_to_create_self_loop(self, clean_db, edge_orchestrator, sample_edge_data):
        # Create edge
        edge = edge_orchestrator.create(clean_db, sample_edge_data)
        
        # Update to create self-loop
        update_data = {'to_node_id': sample_edge_data['from_node_id']}
        
        with pytest.raises(ValidationError) as exc_info:
            edge_orchestrator.update(clean_db, edge['id'], update_data)
        
        assert "Self-loops are not allowed" in str(exc_info.value)

    def test_update_edge_to_create_duplicate(self, clean_db, edge_orchestrator, sample_edge_data, node_orchestrator):
        # Create first edge
        edge1 = edge_orchestrator.create(clean_db, sample_edge_data)
        
        # Create third node
        node_data3 = {
            'workflow_id': sample_edge_data['workflow_id'],
            'name': 'third_node',
            'description': 'Third node for testing',
            'max_retries': 1,
            'params': {}
        }
        node3 = node_orchestrator.create(clean_db, node_data3)
        
        # Create second edge from node1 to node3
        edge_data2 = sample_edge_data.copy()
        edge_data2['to_node_id'] = node3['id']
        edge2 = edge_orchestrator.create(clean_db, edge_data2)
        
        # Try to update edge2 to be duplicate of edge1
        update_data = {'to_node_id': sample_edge_data['to_node_id']}
        
        with pytest.raises(ValidationError) as exc_info:
            edge_orchestrator.update(clean_db, edge2['id'], update_data)
        
        assert "Edge already exists between nodes" in str(exc_info.value)


@pytest.mark.integration
class TestEdgeOrchestrationDelete:
    def test_delete_edge_with_valid_id(self, clean_db, edge_orchestrator, sample_edge_data):
        # Create edge
        edge = edge_orchestrator.create(clean_db, sample_edge_data)
        
        # Delete edge
        result = edge_orchestrator.delete(clean_db, edge['id'])
        
        # Verify response
        assert result is not None
        assert result['id'] == edge['id']
        
        # Verify deletion in database
        db_edge = clean_db.get(Edge, edge['id'])
        assert db_edge is None

    def test_delete_edge_with_invalid_id(self, clean_db, edge_orchestrator):
        # Attempt to delete non-existent edge
        with pytest.raises(BusinessLogicError) as exc_info:
            edge_orchestrator.delete(clean_db, 'INVALID-EDGE-ID')
        
        assert "Edge not found" in str(exc_info.value)


@pytest.mark.integration
class TestEdgeOrchestrationGet:
    def test_get_edge_with_valid_id(self, clean_db, edge_orchestrator, sample_edge_data):
        # Create edge
        edge = edge_orchestrator.create(clean_db, sample_edge_data)
        
        # Get edge
        result = edge_orchestrator.get(clean_db, edge['id'])
        
        # Verify response
        assert result is not None
        assert result['id'] == edge['id']
        assert result['workflow_id'] == sample_edge_data['workflow_id']
        assert result['from_node_id'] == sample_edge_data['from_node_id']
        assert result['to_node_id'] == sample_edge_data['to_node_id']

    def test_get_edge_with_details(self, clean_db, edge_orchestrator, sample_edge_data):
        # Create edge
        edge = edge_orchestrator.create(clean_db, sample_edge_data)
        
        # Get edge with details
        result = edge_orchestrator.get(clean_db, edge['id'], include_details=True)
        
        # Verify response includes additional details
        assert result is not None
        assert result['id'] == edge['id']
        assert 'from_node_name' in result
        assert 'to_node_name' in result
        assert 'workflow_name' in result
        assert result['from_node_name'] == 'source_node'
        assert result['to_node_name'] == 'target_node'
        assert result['workflow_name'] == 'Edge Test Workflow'

    def test_get_edge_with_invalid_id(self, clean_db, edge_orchestrator):
        # Attempt to get non-existent edge
        with pytest.raises(BusinessLogicError) as exc_info:
            edge_orchestrator.get(clean_db, 'INVALID-EDGE-ID')
        
        assert "Edge not found" in str(exc_info.value)


@pytest.mark.integration
class TestEdgeOrchestrationSearch:
    def test_search_edge_with_workflow_criteria(self, clean_db, edge_orchestrator, sample_edge_data):
        # Create edge
        edge = edge_orchestrator.create(clean_db, sample_edge_data)
        
        # Search by workflow_id
        search_criteria = {'workflow_id': sample_edge_data['workflow_id']}
        result = edge_orchestrator.search(clean_db, search_criteria)
        
        # Verify response
        assert result is not None
        assert 'data' in result
        assert 'total_count' in result
        assert result['total_count'] >= 1
        assert len(result['data']) >= 1
        
        # Verify edge is in results
        edge_found = any(e['id'] == edge['id'] for e in result['data'])
        assert edge_found

    def test_search_edge_with_condition_criteria(self, clean_db, edge_orchestrator, sample_edge_data):
        # Create edge with condition
        edge = edge_orchestrator.create(clean_db, sample_edge_data)
        
        # Search by condition_type (use lowercase as defined in enum)
        search_criteria = {'condition_type': 'success'}
        result = edge_orchestrator.search(clean_db, search_criteria)
        
        # Verify response
        assert result is not None
        assert result['total_count'] >= 1
        
        # Verify all results have success condition
        for edge_data in result['data']:
            assert edge_data['condition_type'] == 'success'

    def test_search_edge_with_pagination(self, clean_db, edge_orchestrator, sample_edge_data, node_orchestrator):
        # Create multiple edges
        edges = []
        for i in range(5):
            # Create additional node
            node_data = {
                'workflow_id': sample_edge_data['workflow_id'],
                'name': f'node_{i}',
                'description': f'Node {i} for pagination testing',
                'max_retries': 1,
                'params': {}
            }
            node = node_orchestrator.create(clean_db, node_data)
            
            # Create edge
            edge_data = sample_edge_data.copy()
            edge_data['to_node_id'] = node['id']
            edge = edge_orchestrator.create(clean_db, edge_data)
            edges.append(edge)
        
        # Search with pagination
        search_criteria = {'workflow_id': sample_edge_data['workflow_id']}
        result = edge_orchestrator.search(clean_db, search_criteria, skip=0, limit=3)
        
        # Verify pagination
        assert result is not None
        assert len(result['data']) <= 3
        assert result['total_count'] >= 5
        assert result['skip'] == 0
        assert result['limit'] == 3
        assert result['has_more'] == True

    def test_search_edge_with_invalid_criteria(self, clean_db, edge_orchestrator):
        # Search with criteria that matches nothing
        search_criteria = {'workflow_id': 'NON-EXISTENT-WORKFLOW'}
        result = edge_orchestrator.search(clean_db, search_criteria)
        
        # Verify empty result
        assert result is not None
        assert result['total_count'] == 0
        assert len(result['data']) == 0


@pytest.mark.integration
class TestEdgeOrchestrationValidate:
    def test_validate_edge_with_valid_id(self, clean_db, edge_orchestrator, sample_edge_data):
        # Create edge
        edge = edge_orchestrator.create(clean_db, sample_edge_data)
        
        # Validate edge
        result = edge_orchestrator.validate(clean_db, edge['id'])
        
        # Verify validation result
        assert result is not None
        assert result['edge_id'] == edge['id']
        assert result['is_valid'] == True
        assert len(result['validation_errors']) == 0

    def test_validate_edge_with_invalid_id(self, clean_db, edge_orchestrator):
        # Attempt to validate non-existent edge
        with pytest.raises(BusinessLogicError) as exc_info:
            edge_orchestrator.validate(clean_db, 'INVALID-EDGE-ID')
        
        assert "Edge not found" in str(exc_info.value)

    def test_validate_edge_with_missing_nodes(self, clean_db, edge_orchestrator, sample_edge_data, node_orchestrator):
        # Create edge
        edge = edge_orchestrator.create(clean_db, sample_edge_data)
        
        # Create a separate node and edge to test with
        node_data_temp = {
            'workflow_id': sample_edge_data['workflow_id'],
            'name': 'temp_node',
            'description': 'Temporary node for testing',
            'max_retries': 1,
            'params': {}
        }
        temp_node = node_orchestrator.create(clean_db, node_data_temp)
        
        # Create edge with temp node
        edge_data_temp = sample_edge_data.copy()
        edge_data_temp['from_node_id'] = temp_node['id']
        temp_edge = edge_orchestrator.create(clean_db, edge_data_temp)
        
        # Now delete the temp_node - but edge might cascade delete too
        # Let's manually update the edge to point to a non-existent node
        from miniflow.database.models import Edge as EdgeModel
        db_edge = clean_db.get(EdgeModel, temp_edge['id'])
        db_edge.from_node_id = 'NON-EXISTENT-NODE-ID'
        clean_db.commit()
        
        # Validate edge
        result = edge_orchestrator.validate(clean_db, temp_edge['id'])
        
        # Verify validation result shows errors
        assert result is not None
        assert result['is_valid'] == False
        assert len(result['validation_errors']) > 0
        assert any("From node not found" in error for error in result['validation_errors'])


@pytest.mark.integration
class TestEdgeOrchestrationExtraOperations:
    def test_count_edges(self, clean_db, edge_orchestrator, sample_edge_data):
        # Get initial count
        initial_count = edge_orchestrator.count(clean_db)
        
        # Create edge
        edge = edge_orchestrator.create(clean_db, sample_edge_data)
        
        # Verify count increased
        new_count = edge_orchestrator.count(clean_db)
        assert new_count == initial_count + 1

    def test_exists_edge_with_valid_id(self, clean_db, edge_orchestrator, sample_edge_data):
        # Create edge
        edge = edge_orchestrator.create(clean_db, sample_edge_data)
        
        # Check existence
        exists = edge_orchestrator.exists(clean_db, edge['id'])
        assert exists == True

    def test_exists_edge_with_invalid_id(self, clean_db, edge_orchestrator):
        # Check non-existent edge
        exists = edge_orchestrator.exists(clean_db, 'INVALID-EDGE-ID')
        assert exists == False

    def test_get_all_edges(self, clean_db, edge_orchestrator, sample_edge_data):
        # Create edge
        edge = edge_orchestrator.create(clean_db, sample_edge_data)
        
        # Get all edges
        result = edge_orchestrator.get_all(clean_db)
        
        # Verify response
        assert result is not None
        assert isinstance(result, list)
        assert len(result) >= 1
        
        # Verify our edge is in the list
        edge_found = any(e['id'] == edge['id'] for e in result)
        assert edge_found

    def test_get_by_workflow(self, clean_db, edge_orchestrator, sample_edge_data, workflow_orchestrator):
        # Create edge in first workflow
        edge1 = edge_orchestrator.create(clean_db, sample_edge_data)
        
        # Create second workflow with nodes
        workflow_data2 = {
            'name': 'Second Workflow',
            'description': 'Second workflow for testing',
            'priority': 3
        }
        workflow2 = workflow_orchestrator.create(clean_db, workflow_data2)
        
        # Get edges by first workflow
        result = edge_orchestrator.get_by_workflow(clean_db, sample_edge_data['workflow_id'])
        
        # Verify response
        assert result is not None
        assert isinstance(result, list)
        assert len(result) >= 1
        
        # Verify all edges belong to the correct workflow
        for edge in result:
            assert edge['workflow_id'] == sample_edge_data['workflow_id']

    def test_get_by_workflow_with_invalid_id(self, clean_db, edge_orchestrator):
        # Attempt to get edges for non-existent workflow
        with pytest.raises(BusinessLogicError) as exc_info:
            edge_orchestrator.get_by_workflow(clean_db, 'INVALID-WORKFLOW-ID')
        
        assert "Workflow not found" in str(exc_info.value)

    def test_get_by_workflow_with_missing_id(self, clean_db, edge_orchestrator):
        # Attempt to get edges with empty workflow_id
        with pytest.raises(ValidationError) as exc_info:
            edge_orchestrator.get_by_workflow(clean_db, '')
        
        assert "Workflow ID is required" in str(exc_info.value)
