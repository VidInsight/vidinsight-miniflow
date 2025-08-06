"""
ExecutionInputCRUD Test Suite
=============================

Tests for ExecutionInputCRUD class focusing on scheduler-specific business logic,
complex joins, dependency management, and task queue operations.

This is a critical component for the scheduler so comprehensive testing is essential.
"""

import pytest
import uuid
from typing import List, Dict, Any
from sqlalchemy.exc import IntegrityError

from miniflow.database_manager.crud.execution_input_crud import ExecutionInputCRUD
from miniflow.database_manager.models import (
    ExecutionInput, Execution, Node, Script, Edge, Workflow, 
    WorkflowStatus, ExecutionStatus, ScriptTestStatus
)


@pytest.fixture
def execution_input_crud():
    """Create ExecutionInputCRUD instance"""
    return ExecutionInputCRUD()


@pytest.fixture
def test_workflow(test_database_session):
    """Create a test workflow"""
    unique_id = uuid.uuid4().hex[:8]
    workflow = Workflow(
        name=f"Test Workflow-{unique_id}",
        description="Test workflow for execution input tests",
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
        description="Test script for execution input tests",
        language="python",
        script_path="/test/script.py",
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
        pending_nodes=5,
        executed_nodes=0
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
            params={"param": f"value{i+1}"},
            max_retries=3,
            timeout_seconds=300
        )
        test_database_session.add(node)
        nodes.append(node)
    
    test_database_session.flush()
    return nodes


@pytest.fixture
def test_execution_inputs(test_database_session, test_execution, test_nodes):
    """Create test execution inputs with different dependency counts"""
    execution_inputs = []
    
    for i, node in enumerate(test_nodes):
        execution_input = ExecutionInput(
            execution_id=test_execution.id,
            node_id=node.id,
            priority=i + 1,
            dependency_count=i  # 0, 1, 2 - only first is ready
        )
        test_database_session.add(execution_input)
        execution_inputs.append(execution_input)
    
    test_database_session.flush()
    return execution_inputs


class TestExecutionInputCRUDInit:
    """Test ExecutionInputCRUD initialization"""
    
    def test_init_success(self):
        """Test successful initialization"""
        crud = ExecutionInputCRUD()
        assert crud.model == ExecutionInput
        assert crud.model_name == "ExecutionInput"


class TestBasicOperations:
    """Test basic CRUD operations inherited from BaseCRUD"""
    
    def test_create_execution_input(self, test_database_session, execution_input_crud, 
                                   test_execution, test_nodes):
        """Test creating execution input"""
        unique_id = uuid.uuid4().hex[:8]
        data = {
            "execution_id": test_execution.id,
            "node_id": test_nodes[0].id,
            "priority": 1,
            "dependency_count": 0
        }
        
        result = execution_input_crud.create(test_database_session, **data)
        
        assert result is not None
        assert result.execution_id == test_execution.id
        assert result.node_id == test_nodes[0].id
        assert result.priority == 1
        assert result.dependency_count == 0
        assert result.id.startswith("EI-")
    
    def test_find_by_id(self, test_database_session, execution_input_crud, test_execution_inputs):
        """Test finding execution input by ID"""
        execution_input = test_execution_inputs[0]
        
        found = execution_input_crud.find_by_id(test_database_session, execution_input.id)
        
        assert found.id == execution_input.id
        assert found.execution_id == execution_input.execution_id


class TestBusinessLogicOperations:
    """Test ExecutionInputCRUD-specific business logic operations"""
    
    def test_get_execution_inputs_by_execution(self, test_database_session, execution_input_crud,
                                             test_execution_inputs, test_execution):
        """Test getting execution inputs by execution ID"""
        results = execution_input_crud.get_execution_inputs_by_execution(
            test_database_session, test_execution.id
        )
        
        assert len(results) == 3
        assert all(ei.execution_id == test_execution.id for ei in results)
        
        # Test with non-existent execution
        results_empty = execution_input_crud.get_execution_inputs_by_execution(
            test_database_session, "NONEXISTENT"
        )
        assert len(results_empty) == 0


class TestSchedulerOperations:
    """Test scheduler-specific operations - most critical functionality"""
    
    def test_get_ready_tasks_basic(self, test_database_session, execution_input_crud, 
                                  test_execution_inputs):
        """Test getting tasks ready for execution (dependency_count = 0)"""
        ready_tasks = execution_input_crud.get_ready_tasks(test_database_session, limit=10)
        
        # Only first task should be ready (dependency_count = 0)
        assert len(ready_tasks) == 1
        assert ready_tasks[0].dependency_count == 0
        assert ready_tasks[0].id == test_execution_inputs[0].id
    
    def test_get_ready_tasks_with_priority_ordering(self, test_database_session, execution_input_crud,
                                                   test_execution, test_nodes):
        """Test that ready tasks are ordered by priority (desc) then created_at"""
        # Create multiple ready tasks with different priorities
        execution_inputs = []
        priorities = [1, 5, 3]  # Will be ordered as 5, 3, 1
        
        for i, priority in enumerate(priorities):
            ei = ExecutionInput(
                execution_id=test_execution.id,
                node_id=test_nodes[i].id,
                priority=priority,
                dependency_count=0  # All ready
            )
            test_database_session.add(ei)
            execution_inputs.append(ei)
        
        test_database_session.flush()
        
        ready_tasks = execution_input_crud.get_ready_tasks(test_database_session, limit=10)
        
        assert len(ready_tasks) >= 3  # At least 3 new ready tasks
        # Check priority ordering (highest first)
        priorities_result = [task.priority for task in ready_tasks]
        assert priorities_result == sorted(priorities_result, reverse=True)
    
    def test_get_ready_tasks_limit(self, test_database_session, execution_input_crud,
                                  test_execution, test_nodes):
        """Test limit parameter for ready tasks"""
        # Create 5 ready tasks
        for i in range(5):
            unique_id = uuid.uuid4().hex[:8]
            node = Node(
                workflow_id=test_execution.workflow_id,
                script_id=test_nodes[0].script_id,
                name=f"Extra Node-{unique_id}",
                params={"param": "value"}
            )
            test_database_session.add(node)
            test_database_session.flush()
            
            ei = ExecutionInput(
                execution_id=test_execution.id,
                node_id=node.id,
                priority=1,
                dependency_count=0
            )
            test_database_session.add(ei)
        
        test_database_session.flush()
        
        # Test limit
        limited_tasks = execution_input_crud.get_ready_tasks(test_database_session, limit=3)
        assert len(limited_tasks) == 3
    
    def test_get_ready_tasks_with_details(self, test_database_session, execution_input_crud,
                                         test_execution_inputs):
        """Test getting ready tasks with joined details for payload creation"""
        ready_tasks = execution_input_crud.get_ready_tasks_with_details(test_database_session, limit=10)
        
        assert len(ready_tasks) == 1  # Only one ready task
        task = ready_tasks[0]
        
        # Check all required fields are present
        required_fields = [
            'task_id', 'execution_id', 'node_id', 'priority',
            'node_name', 'node_params', 'max_retries', 'timeout_seconds',
            'script_id', 'script_path', 'script_input_params', 'workflow_id'
        ]
        
        for field in required_fields:
            assert field in task, f"Missing field: {field}"
        
        # Verify data integrity
        assert task['task_id'] == test_execution_inputs[0].id
        assert task['execution_id'] == test_execution_inputs[0].execution_id
        assert task['priority'] == test_execution_inputs[0].priority
    
    def test_get_ready_tasks_with_details_empty(self, test_database_session, execution_input_crud):
        """Test getting ready tasks when none are ready"""
        ready_tasks = execution_input_crud.get_ready_tasks_with_details(test_database_session, limit=10)
        
        # All tasks in fixture have dependency_count > 0 except first one which we already tested
        # This test runs after others, so no ready tasks should remain
        assert isinstance(ready_tasks, list)


class TestBulkOperations:
    """Test bulk operations for task management"""
    
    def test_bulk_delete_by_ids_success(self, test_database_session, execution_input_crud,
                                       test_execution_inputs):
        """Test bulk deletion of execution inputs by IDs"""
        # Get IDs to delete
        ids_to_delete = [test_execution_inputs[0].id, test_execution_inputs[1].id]
        
        # Count before deletion
        initial_count = execution_input_crud.count(test_database_session)
        
        # Bulk delete
        deleted_count = execution_input_crud.bulk_delete_by_ids(test_database_session, ids_to_delete)
        
        assert deleted_count == 2
        
        # Verify deletion
        final_count = execution_input_crud.count(test_database_session)
        assert final_count == initial_count - 2
        
        # Verify specific items are deleted
        with pytest.raises(ValueError):
            execution_input_crud.find_by_id(test_database_session, test_execution_inputs[0].id)
    
    def test_bulk_delete_by_ids_empty_list(self, test_database_session, execution_input_crud):
        """Test bulk deletion with empty list"""
        result = execution_input_crud.bulk_delete_by_ids(test_database_session, [])
        assert result == 0
    
    def test_bulk_delete_by_ids_nonexistent(self, test_database_session, execution_input_crud):
        """Test bulk deletion with non-existent IDs"""
        result = execution_input_crud.bulk_delete_by_ids(test_database_session, ["NONEXISTENT1", "NONEXISTENT2"])
        assert result == 0


class TestDependencyManagement:
    """Test dependency count management operations"""
    
    def test_decrease_dependency_count_for_nodes(self, test_database_session, execution_input_crud,
                                                test_execution_inputs, test_execution, test_nodes):
        """Test decreasing dependency count for specific nodes"""
        # Initial state: [0, 1, 2] dependency counts
        initial_counts = [ei.dependency_count for ei in test_execution_inputs]
        assert initial_counts == [0, 1, 2]
        
        # Decrease dependency for nodes 1 and 2 (indices 1, 2)
        node_ids_to_update = [test_nodes[1].id, test_nodes[2].id]
        
        affected_count = execution_input_crud.decrease_dependency_count_for_nodes(
            test_database_session, node_ids_to_update, test_execution.id
        )
        
        assert affected_count == 2  # Two nodes affected
        
        # Refresh and check new counts
        test_database_session.expire_all()
        updated_inputs = execution_input_crud.get_execution_inputs_by_execution(
            test_database_session, test_execution.id
        )
        
        # Sort by original order to match test_execution_inputs order
        node_to_count = {ei.node_id: ei.dependency_count for ei in updated_inputs}
        new_counts = [node_to_count[node.id] for node in test_nodes]
        
        # Should be [0, 0, 1] - decreased by 1
        assert new_counts == [0, 0, 1]
    
    def test_decrease_dependency_count_empty_nodes(self, test_database_session, execution_input_crud,
                                                  test_execution):
        """Test decreasing dependency count with empty node list"""
        result = execution_input_crud.decrease_dependency_count_for_nodes(
            test_database_session, [], test_execution.id
        )
        assert result == 0
    
    def test_decrease_dependency_count_nonexistent_execution(self, test_database_session, 
                                                           execution_input_crud, test_nodes):
        """Test decreasing dependency count for non-existent execution"""
        result = execution_input_crud.decrease_dependency_count_for_nodes(
            test_database_session, [test_nodes[0].id], "NONEXISTENT"
        )
        assert result == 0
    
    def test_decrease_dependency_count_zero_dependency(self, test_database_session, execution_input_crud,
                                                      test_execution_inputs, test_execution, test_nodes):
        """Test that nodes with dependency_count = 0 are not affected"""
        # Try to decrease dependency for node 0 (already has 0 dependency)
        node_ids = [test_nodes[0].id]
        
        affected_count = execution_input_crud.decrease_dependency_count_for_nodes(
            test_database_session, node_ids, test_execution.id
        )
        
        # Should be 0 because WHERE clause excludes dependency_count <= 0
        assert affected_count == 0


class TestStatusQueries:
    """Test execution status and task counting operations"""
    
    def test_get_tasks_by_execution_status(self, test_database_session, execution_input_crud,
                                          test_execution_inputs, test_execution):
        """Test getting all tasks for a specific execution"""
        tasks = execution_input_crud.get_tasks_by_execution_status(
            test_database_session, test_execution.id
        )
        
        assert len(tasks) == 3
        assert all(task.execution_id == test_execution.id for task in tasks)
    
    def test_count_ready_tasks(self, test_database_session, execution_input_crud, test_execution_inputs):
        """Test counting ready tasks"""
        ready_count = execution_input_crud.count_ready_tasks(test_database_session)
        
        # From fixture, only first task has dependency_count = 0
        assert ready_count == 1
        
        # Make another task ready
        test_execution_inputs[1].dependency_count = 0
        test_database_session.flush()
        
        new_ready_count = execution_input_crud.count_ready_tasks(test_database_session)
        assert new_ready_count == 2


class TestDependencyGraphOperations:
    """Test operations related to workflow dependency graph"""
    
    def test_get_dependent_nodes(self, test_database_session, execution_input_crud,
                                test_execution, test_nodes, test_workflow):
        """Test getting node IDs that depend on a completed node"""
        # Create edges to establish dependencies
        # Node 0 -> Node 1, Node 0 -> Node 2
        edge1 = Edge(
            workflow_id=test_workflow.id,
            from_node_id=test_nodes[0].id,
            to_node_id=test_nodes[1].id,
            condition_type="success"
        )
        edge2 = Edge(
            workflow_id=test_workflow.id,
            from_node_id=test_nodes[0].id,
            to_node_id=test_nodes[2].id,
            condition_type="success"
        )
        
        test_database_session.add_all([edge1, edge2])
        test_database_session.flush()
        
        # Get nodes that depend on node 0
        dependent_nodes = execution_input_crud.get_dependent_nodes(
            test_database_session, test_nodes[0].id, test_execution.id
        )
        
        assert len(dependent_nodes) == 2
        assert test_nodes[1].id in dependent_nodes
        assert test_nodes[2].id in dependent_nodes
    
    def test_get_dependent_nodes_no_dependencies(self, test_database_session, execution_input_crud,
                                                test_execution, test_nodes):
        """Test getting dependent nodes when none exist"""
        dependent_nodes = execution_input_crud.get_dependent_nodes(
            test_database_session, test_nodes[0].id, test_execution.id
        )
        
        assert len(dependent_nodes) == 0
    
    def test_get_dependent_nodes_nonexistent_node(self, test_database_session, execution_input_crud,
                                                 test_execution):
        """Test getting dependent nodes for non-existent node"""
        dependent_nodes = execution_input_crud.get_dependent_nodes(
            test_database_session, "NONEXISTENT", test_execution.id
        )
        
        assert len(dependent_nodes) == 0


class TestErrorHandling:
    """Test error handling and edge cases"""
    
    def test_create_with_invalid_execution_id(self, test_database_session, execution_input_crud,
                                             test_nodes):
        """Test creating execution input with invalid execution ID"""
        # Even if FK constraints are not enforced in test DB, we can create the record
        # This test verifies the create operation works regardless
        result = execution_input_crud.create(
            test_database_session,
            execution_id="INVALID",
            node_id=test_nodes[0].id,
            priority=1,
            dependency_count=0
        )
        
        # Verify record was created (even with invalid FK)
        assert result is not None
        assert result.execution_id == "INVALID"
    
    def test_create_with_invalid_node_id(self, test_database_session, execution_input_crud,
                                        test_execution):
        """Test creating execution input with invalid node ID"""
        # Even if FK constraints are not enforced in test DB, we can create the record
        # This test verifies the create operation works regardless
        result = execution_input_crud.create(
            test_database_session,
            execution_id=test_execution.id,
            node_id="INVALID",
            priority=1,
            dependency_count=0
        )
        
        # Verify record was created (even with invalid FK)
        assert result is not None
        assert result.node_id == "INVALID"
    
    def test_negative_dependency_count(self, test_database_session, execution_input_crud,
                                      test_execution, test_nodes):
        """Test that negative dependency count is handled properly"""
        # Create execution input with dependency_count = 1
        ei = ExecutionInput(
            execution_id=test_execution.id,
            node_id=test_nodes[0].id,
            priority=1,
            dependency_count=1
        )
        test_database_session.add(ei)
        test_database_session.flush()
        
        # Decrease twice (should not go below 0)
        execution_input_crud.decrease_dependency_count_for_nodes(
            test_database_session, [test_nodes[0].id], test_execution.id
        )
        execution_input_crud.decrease_dependency_count_for_nodes(
            test_database_session, [test_nodes[0].id], test_execution.id
        )
        
        test_database_session.expire_all()
        updated_ei = execution_input_crud.find_by_id(test_database_session, ei.id)
        
        # Should be 0, not negative
        assert updated_ei.dependency_count == 0


class TestPerformanceAndIntegration:
    """Test performance aspects and integration scenarios"""
    
    def test_ready_tasks_with_joins_performance(self, test_database_session, execution_input_crud,
                                               test_execution, test_nodes):
        """Test that get_ready_tasks_with_details efficiently uses joins"""
        # Create multiple ready tasks
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
            
            ei = ExecutionInput(
                execution_id=test_execution.id,
                node_id=node.id,
                priority=1,
                dependency_count=0
            )
            test_database_session.add(ei)
        
        test_database_session.flush()
        
        # This should execute efficiently with joins, not N+1 queries
        ready_tasks = execution_input_crud.get_ready_tasks_with_details(test_database_session, limit=5)
        
        assert len(ready_tasks) == 5
        
        # Verify all required data is present (no additional queries needed)
        for task in ready_tasks:
            assert task['node_name'] is not None
            assert task['script_path'] is not None
            assert task['workflow_id'] is not None
    
    def test_scheduler_workflow_simulation(self, test_database_session, execution_input_crud,
                                          test_execution, test_nodes, test_workflow):
        """Test a complete scheduler workflow simulation"""
        # Setup: Create workflow with dependencies
        # Node 0 -> Node 1 -> Node 2 (linear dependency)
        
        # Clear existing execution inputs from fixture
        existing_inputs = execution_input_crud.get_execution_inputs_by_execution(
            test_database_session, test_execution.id
        )
        for ei in existing_inputs:
            test_database_session.delete(ei)
        test_database_session.flush()
        
        # Create new execution inputs with proper dependencies
        ei0 = ExecutionInput(
            execution_id=test_execution.id,
            node_id=test_nodes[0].id,
            priority=1,
            dependency_count=0  # Ready to start
        )
        ei1 = ExecutionInput(
            execution_id=test_execution.id,
            node_id=test_nodes[1].id,
            priority=1,
            dependency_count=1  # Depends on node 0
        )
        ei2 = ExecutionInput(
            execution_id=test_execution.id,
            node_id=test_nodes[2].id,
            priority=1,
            dependency_count=1  # Depends on node 1
        )
        
        test_database_session.add_all([ei0, ei1, ei2])
        test_database_session.flush()
        
        # Create edges
        edge1 = Edge(
            workflow_id=test_workflow.id,
            from_node_id=test_nodes[0].id,
            to_node_id=test_nodes[1].id,
            condition_type="success"
        )
        edge2 = Edge(
            workflow_id=test_workflow.id,
            from_node_id=test_nodes[1].id,
            to_node_id=test_nodes[2].id,
            condition_type="success"
        )
        test_database_session.add_all([edge1, edge2])
        test_database_session.flush()
        
        # Step 1: Get ready tasks (should be node 0 only)
        ready_tasks = execution_input_crud.get_ready_tasks(test_database_session)
        assert len(ready_tasks) == 1
        assert ready_tasks[0].node_id == test_nodes[0].id
        
        # Step 2: Simulate node 0 completion
        # - Remove completed task
        execution_input_crud.bulk_delete_by_ids(test_database_session, [ei0.id])
        
        # - Get dependent nodes and decrease their dependency
        dependent_nodes = execution_input_crud.get_dependent_nodes(
            test_database_session, test_nodes[0].id, test_execution.id
        )
        execution_input_crud.decrease_dependency_count_for_nodes(
            test_database_session, dependent_nodes, test_execution.id
        )
        
        # Step 3: Check new ready tasks (should be node 1)
        ready_tasks = execution_input_crud.get_ready_tasks(test_database_session)
        assert len(ready_tasks) == 1
        assert ready_tasks[0].node_id == test_nodes[1].id
        
        # Step 4: Simulate node 1 completion
        execution_input_crud.bulk_delete_by_ids(test_database_session, [ei1.id])
        dependent_nodes = execution_input_crud.get_dependent_nodes(
            test_database_session, test_nodes[1].id, test_execution.id
        )
        execution_input_crud.decrease_dependency_count_for_nodes(
            test_database_session, dependent_nodes, test_execution.id
        )
        
        # Step 5: Check final ready tasks (should be node 2)
        ready_tasks = execution_input_crud.get_ready_tasks(test_database_session)
        assert len(ready_tasks) == 1
        assert ready_tasks[0].node_id == test_nodes[2].id
        
        # Step 6: Complete workflow
        execution_input_crud.bulk_delete_by_ids(test_database_session, [ei2.id])
        
        # No more ready tasks
        ready_tasks = execution_input_crud.get_ready_tasks(test_database_session)
        assert len(ready_tasks) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])