"""
ExecutionOutputCRUD Test Suite
==============================

Tests for ExecutionOutputCRUD class focusing on result processing,
dynamic parameter resolution, and output collection operations.

This is critical for result collection and parameter passing between nodes.
"""

import pytest
import uuid
from typing import List, Dict, Any
from sqlalchemy.exc import IntegrityError

from miniflow.database_manager.crud.execution_output_crud import ExecutionOutputCRUD
from miniflow.database_manager.models import (
    ExecutionOutput, Execution, Node, Script, Workflow,
    WorkflowStatus, ExecutionStatus, ExecutionOutputStatus, ScriptTestStatus
)


@pytest.fixture
def execution_output_crud():
    """Create ExecutionOutputCRUD instance"""
    return ExecutionOutputCRUD()


@pytest.fixture
def test_workflow(test_database_session):
    """Create a test workflow"""
    unique_id = uuid.uuid4().hex[:8]
    workflow = Workflow(
        name=f"Test Workflow-{unique_id}",
        description="Test workflow for execution output tests",
        status=WorkflowStatus.ACTIVE
    )
    test_database_session.add(workflow)
    test_database_session.flush()
    return workflow


@pytest.fixture
def test_script(test_database_session):
    """Create a test script"""
    unique_id = uuid.uuid4().hex[:8]
    script = Script(
        name=f"Test Script-{unique_id}",
        description="Test script for execution output tests",
        language="python",
        script_path="/test/script.py",
        output_params={"result": "string", "status": "bool", "count": "int"},
        test_status=ScriptTestStatus.PASSED
    )
    test_database_session.add(script)
    test_database_session.flush()
    return script


@pytest.fixture
def test_execution(test_database_session, test_workflow):
    """Create a test execution"""
    execution = Execution(
        workflow_id=test_workflow.id,
        status=ExecutionStatus.RUNNING,
        pending_nodes=3,
        executed_nodes=2
    )
    test_database_session.add(execution)
    test_database_session.flush()
    return execution


@pytest.fixture
def test_nodes(test_database_session, test_workflow, test_script):
    """Create test nodes"""
    nodes = []
    for i in range(3):
        unique_id = uuid.uuid4().hex[:8]
        node = Node(
            workflow_id=test_workflow.id,
            script_id=test_script.id,
            name=f"Test Node {i+1}-{unique_id}",
            params={"input_param": f"value{i+1}"},
            max_retries=3,
            timeout_seconds=300
        )
        test_database_session.add(node)
        nodes.append(node)
    
    test_database_session.flush()
    return nodes


@pytest.fixture
def test_execution_outputs(test_database_session, test_execution, test_nodes):
    """Create test execution outputs with different statuses"""
    execution_outputs = []
    statuses = [ExecutionOutputStatus.SUCCESS, ExecutionOutputStatus.FAILURE, ExecutionOutputStatus.TIMEOUT]
    
    for i, (node, status) in enumerate(zip(test_nodes, statuses)):
        execution_output = ExecutionOutput(
            execution_id=test_execution.id,
            node_id=node.id,
            status=status,
            result_data={
                "result": f"output_{i+1}",
                "status": status == ExecutionOutputStatus.SUCCESS,
                "count": (i + 1) * 10,
                "timestamp": f"2024-01-{i+1:02d}T10:00:00Z"
            }
        )
        test_database_session.add(execution_output)
        execution_outputs.append(execution_output)
    
    test_database_session.flush()
    return execution_outputs


class TestExecutionOutputCRUDInit:
    """Test ExecutionOutputCRUD initialization"""
    
    def test_init_success(self):
        """Test successful initialization"""
        crud = ExecutionOutputCRUD()
        assert crud.model == ExecutionOutput
        assert crud.model_name == "ExecutionOutput"


class TestBasicOperations:
    """Test basic CRUD operations inherited from BaseCRUD"""
    
    def test_create_execution_output(self, test_database_session, execution_output_crud,
                                   test_execution, test_nodes):
        """Test creating execution output"""
        data = {
            "execution_id": test_execution.id,
            "node_id": test_nodes[0].id,
            "status": ExecutionOutputStatus.SUCCESS,
            "result_data": {"result": "test_result", "count": 42}
        }
        
        result = execution_output_crud.create(test_database_session, **data)
        
        assert result is not None
        assert result.execution_id == test_execution.id
        assert result.node_id == test_nodes[0].id
        assert result.status == ExecutionOutputStatus.SUCCESS
        assert result.result_data["result"] == "test_result"
        assert result.result_data["count"] == 42
        assert result.id.startswith("EO-")
    
    def test_find_by_id(self, test_database_session, execution_output_crud, test_execution_outputs):
        """Test finding execution output by ID"""
        execution_output = test_execution_outputs[0]
        
        found = execution_output_crud.find_by_id(test_database_session, execution_output.id)
        
        assert found.id == execution_output.id
        assert found.execution_id == execution_output.execution_id
        assert found.status == ExecutionOutputStatus.SUCCESS


class TestBusinessLogicOperations:
    """Test ExecutionOutputCRUD-specific business logic operations"""
    
    def test_get_execution_outputs_by_execution(self, test_database_session, execution_output_crud,
                                               test_execution_outputs, test_execution):
        """Test getting execution outputs by execution ID"""
        results = execution_output_crud.get_execution_outputs_by_execution(
            test_database_session, test_execution.id
        )
        
        assert len(results) == 3
        assert all(eo.execution_id == test_execution.id for eo in results)
        
        # Verify different statuses are present
        statuses = {eo.status for eo in results}
        expected_statuses = {ExecutionOutputStatus.SUCCESS, ExecutionOutputStatus.FAILURE, ExecutionOutputStatus.TIMEOUT}
        assert statuses == expected_statuses
        
        # Test with non-existent execution
        results_empty = execution_output_crud.get_execution_outputs_by_execution(
            test_database_session, "NONEXISTENT"
        )
        assert len(results_empty) == 0
    
    def test_get_outputs_by_execution_and_status(self, test_database_session, execution_output_crud,
                                                test_execution_outputs, test_execution):
        """Test getting execution outputs by execution and status"""
        # Get successful outputs
        success_results = execution_output_crud.get_outputs_by_execution_and_status(
            test_database_session, test_execution.id, ExecutionOutputStatus.SUCCESS
        )
        
        assert len(success_results) == 1
        assert success_results[0].status == ExecutionOutputStatus.SUCCESS
        
        # Get failed outputs
        failure_results = execution_output_crud.get_outputs_by_execution_and_status(
            test_database_session, test_execution.id, ExecutionOutputStatus.FAILURE
        )
        
        assert len(failure_results) == 1
        assert failure_results[0].status == ExecutionOutputStatus.FAILURE
    
    def test_get_completed_nodes_for_execution(self, test_database_session, execution_output_crud,
                                              test_execution_outputs, test_execution):
        """Test getting completed node IDs for an execution"""
        completed_nodes = execution_output_crud.get_completed_nodes_for_execution(
            test_database_session, test_execution.id
        )
        
        assert len(completed_nodes) == 1  # Only one SUCCESS status
        assert test_execution_outputs[0].node_id in completed_nodes
    
    def test_check_output_exists(self, test_database_session, execution_output_crud,
                                test_execution_outputs, test_execution, test_nodes):
        """Test checking if execution output exists"""
        # Should exist for first node
        exists = execution_output_crud.check_output_exists(
            test_database_session, test_execution.id, test_nodes[0].id
        )
        assert exists is True
        
        # Should not exist for non-existent node
        exists_false = execution_output_crud.check_output_exists(
            test_database_session, test_execution.id, "NONEXISTENT"
        )
        assert exists_false is False


class TestResultCollection:
    """Test result collection and aggregation operations"""
    
    def test_get_execution_progress(self, test_database_session, execution_output_crud,
                                   test_execution_outputs, test_execution):
        """Test getting execution progress statistics"""
        progress = execution_output_crud.get_execution_progress(
            test_database_session, test_execution.id
        )
        
        # Should have progress data
        assert "total" in progress
        assert "success" in progress
        assert "failure" in progress
        assert "timeout" in progress
        assert "cancelled" in progress
        
        # Verify counts
        assert progress["total"] == 3  # 3 outputs total
        assert progress["success"] == 1  # 1 success
        assert progress["failure"] == 1  # 1 failure
        assert progress["timeout"] == 1  # 1 timeout
        assert progress["cancelled"] == 0  # 0 cancelled
    
    def test_get_execution_progress_empty(self, test_database_session, execution_output_crud):
        """Test getting progress for execution with no outputs"""
        progress = execution_output_crud.get_execution_progress(
            test_database_session, "NONEXISTENT"
        )
        
        # Should return zero counts
        assert progress["total"] == 0
        assert progress["success"] == 0
        assert progress["failure"] == 0


class TestParameterResolution:
    """Test dynamic parameter resolution for dependent nodes"""
    
    def test_get_node_result_data(self, test_database_session, execution_output_crud,
                                 test_execution_outputs, test_execution, test_nodes):
        """Test getting result data for a specific node by name"""
        # Get result data from successful node
        successful_node = test_nodes[0]
        result_data = execution_output_crud.get_node_result_data(
            test_database_session, test_execution.id, successful_node.name
        )
        
        assert result_data is not None
        assert result_data["result"] == "output_1"
        assert result_data["status"] is True
        assert result_data["count"] == 10
        
        # Test with non-existent node name
        nonexistent_result = execution_output_crud.get_node_result_data(
            test_database_session, test_execution.id, "Nonexistent Node"
        )
        
        assert nonexistent_result == {}  # Should return empty dict
    
    def test_get_execution_results_for_dependency_resolution(self, test_database_session, execution_output_crud,
                                                            test_execution_outputs, test_execution, test_nodes):
        """Test getting execution results for dependency resolution"""
        # Get results for specific nodes
        node_ids = [test_nodes[0].id, test_nodes[1].id]
        dependency_data = execution_output_crud.get_execution_results_for_dependency_resolution(
            test_database_session, test_execution.id, node_ids
        )
        
        # Should only return successful nodes
        assert len(dependency_data) == 1  # Only successful node
        assert test_nodes[0].id in dependency_data
        
        # Verify structure
        node_data = dependency_data[test_nodes[0].id]
        assert "node_name" in node_data
        assert "result_data" in node_data
        assert node_data["node_name"] == test_nodes[0].name
        assert node_data["result_data"]["result"] == "output_1"
        
        # Test with empty node list
        empty_results = execution_output_crud.get_execution_results_for_dependency_resolution(
            test_database_session, test_execution.id, []
        )
        assert empty_results == {}


class TestStatusOperations:
    """Test status-based query operations"""
    
    def test_count_outputs_by_status(self, test_database_session, execution_output_crud,
                                    test_execution_outputs, test_execution):
        """Test counting outputs by status for an execution"""
        # Count by individual statuses
        success_count = execution_output_crud.count_outputs_by_status(
            test_database_session, test_execution.id, ExecutionOutputStatus.SUCCESS
        )
        failure_count = execution_output_crud.count_outputs_by_status(
            test_database_session, test_execution.id, ExecutionOutputStatus.FAILURE
        )
        timeout_count = execution_output_crud.count_outputs_by_status(
            test_database_session, test_execution.id, ExecutionOutputStatus.TIMEOUT
        )
        
        assert success_count == 1
        assert failure_count == 1
        assert timeout_count == 1
    
    def test_get_completion_summary(self, test_database_session, execution_output_crud,
                                   test_execution_outputs, test_execution):
        """Test getting completion summary for an execution"""
        summary = execution_output_crud.get_completion_summary(
            test_database_session, test_execution.id
        )
        
        expected_summary = {
            "total_outputs": 3,
            "successful": 1,
            "failed": 1,
            "timeout": 1,
            "cancelled": 0,
            "success_rate": 33.33  # 1/3 * 100, rounded to 2 decimals
        }
        
        assert summary == expected_summary
    
    def test_get_completion_summary_empty(self, test_database_session, execution_output_crud):
        """Test getting completion summary for execution with no outputs"""
        summary = execution_output_crud.get_completion_summary(
            test_database_session, "NONEXISTENT"
        )
        
        expected_summary = {
            "total_outputs": 0,
            "successful": 0,
            "failed": 0,
            "timeout": 0,
            "cancelled": 0,
            "success_rate": 0.0
        }
        
        assert summary == expected_summary


class TestErrorHandling:
    """Test error handling and edge cases"""
    
    def test_create_with_invalid_execution_id(self, test_database_session, execution_output_crud,
                                             test_nodes):
        """Test creating execution output with invalid execution ID"""
        # Test that record can be created even with invalid FK (if constraints not enforced)
        result = execution_output_crud.create(
            test_database_session,
            execution_id="INVALID",
            node_id=test_nodes[0].id,
            status=ExecutionOutputStatus.SUCCESS,
            result_data={"result": "test"}
        )
        
        assert result is not None
        assert result.execution_id == "INVALID"
    
    def test_create_with_invalid_node_id(self, test_database_session, execution_output_crud,
                                        test_execution):
        """Test creating execution output with invalid node ID"""
        # Test that record can be created even with invalid FK (if constraints not enforced)
        result = execution_output_crud.create(
            test_database_session,
            execution_id=test_execution.id,
            node_id="INVALID",
            status=ExecutionOutputStatus.SUCCESS,
            result_data={"result": "test"}
        )
        
        assert result is not None
        assert result.node_id == "INVALID"
    
    def test_create_with_empty_output_data(self, test_database_session, execution_output_crud,
                                          test_execution, test_nodes):
        """Test creating execution output with empty output data"""
        result = execution_output_crud.create(
            test_database_session,
            execution_id=test_execution.id,
            node_id=test_nodes[0].id,
            status=ExecutionOutputStatus.SUCCESS,
            result_data={}
        )
        
        assert result is not None
        assert result.output_data == {}
    
    def test_parameter_resolution_with_malformed_template(self, test_database_session, execution_output_crud,
                                                         test_execution):
        """Test parameter resolution with malformed templates"""
        malformed_templates = [
            {"param": "{{incomplete_template"},  # Missing closing brace
            {"param": "{{.missing_node_id}}"},   # Missing node ID
            {"param": "{{node_123.}}"},          # Missing field name
            {"param": "{{}}"},                   # Empty template
        ]
        
        for template in malformed_templates:
            # Should not raise exception, should leave malformed templates unchanged
            resolved = execution_output_crud.resolve_dynamic_parameters(
                test_database_session, test_execution.id, template
            )
            assert resolved == template  # Should be unchanged


class TestPerformanceAndIntegration:
    """Test performance aspects and integration scenarios"""
    
    def test_bulk_result_collection_performance(self, test_database_session, execution_output_crud,
                                               test_execution, test_nodes):
        """Test performance of bulk result collection"""
        # Create many outputs for performance testing
        for i in range(10):
            unique_id = uuid.uuid4().hex[:8]
            node = Node(
                workflow_id=test_execution.workflow_id,
                script_id=test_nodes[0].script_id,
                name=f"Perf Node-{unique_id}",
                params={"param": "value"}
            )
            test_database_session.add(node)
            test_database_session.flush()
            
            output = ExecutionOutput(
                execution_id=test_execution.id,
                node_id=node.id,
                status=ExecutionOutputStatus.SUCCESS,
                result_data={"result": f"result_{i}", "index": i}
            )
            test_database_session.add(output)
        
        test_database_session.flush()
        
        # This should execute efficiently with a single query
        results_dict = execution_output_crud.collect_results_for_execution(
            test_database_session, test_execution.id
        )
        
        assert len(results_dict) >= 10
    
    def test_parameter_resolution_workflow_simulation(self, test_database_session, execution_output_crud,
                                                     test_execution, test_nodes):
        """Test complete parameter resolution workflow simulation"""
        # Simulate a workflow where Node 2 depends on output from Node 1
        
        # Step 1: Node 1 completes successfully
        node1_output = ExecutionOutput(
            execution_id=test_execution.id,
            node_id=test_nodes[0].id,
            status=ExecutionOutputStatus.SUCCESS,
            result_data={
                "user_id": "user123",
                "processed_count": 50,
                "status": "completed",
                "file_path": "/data/processed_file.csv"
            }
        )
        test_database_session.add(node1_output)
        test_database_session.flush()
        
        # Step 2: Node 2 needs to use Node 1's output as parameters
        node2_param_template = {
            "input_file": "{{node_" + test_nodes[0].id + ".file_path}}",
            "user_id": "{{node_" + test_nodes[0].id + ".user_id}}",
            "expected_count": "{{node_" + test_nodes[0].id + ".processed_count}}",
            "static_config": {"timeout": 300, "retries": 3}
        }
        
        # Step 3: Resolve parameters for Node 2
        resolved_params = execution_output_crud.resolve_dynamic_parameters(
            test_database_session, test_execution.id, node2_param_template
        )
        
        # Step 4: Verify resolution
        expected_params = {
            "input_file": "/data/processed_file.csv",
            "user_id": "user123",
            "expected_count": 50,
            "static_config": {"timeout": 300, "retries": 3}
        }
        
        assert resolved_params == expected_params
        
        # Step 5: Node 2 executes with resolved parameters and produces output
        node2_output = ExecutionOutput(
            execution_id=test_execution.id,
            node_id=test_nodes[1].id,
            status=ExecutionOutputStatus.SUCCESS,
            result_data={
                "validation_result": "passed",
                "processed_records": 50,
                "output_file": "/data/validated_file.csv"
            }
        )
        test_database_session.add(node2_output)
        test_database_session.flush()
        
        # Step 6: Collect final results
        final_results = execution_output_crud.collect_results_for_execution(
            test_database_session, test_execution.id
        )
        
        # Should have results from both nodes plus original fixture data
        assert len(final_results) >= 2
        
        # Verify node 1 and node 2 results are present
        node1_result = final_results[test_nodes[0].id]
        node2_result = final_results[test_nodes[1].id]
        
        assert node1_result["status"] == "success"
        assert node1_result["output_data"]["user_id"] == "user123"
        
        assert node2_result["status"] == "success"
        assert node2_result["output_data"]["validation_result"] == "passed"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])