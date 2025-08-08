"""
Manual tests for DatabaseOrchestration execution functions
Run these tests manually to verify execution operations
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from miniflow.database_manager.engine import DatabaseEngine
from miniflow.database_manager.config import get_sqlite_config
from miniflow.database_manager.orchestration import DatabaseOrchestration
from miniflow.database_manager.models import Base
from miniflow.exceptions import ValidationError, BusinessLogicError
import time

def test_execution_start():
    """Test execution start functionality"""
    print("=== Testing Execution Start ===")
    
    config = get_sqlite_config(db_name='test_execution.db')
    engine = DatabaseEngine(config)
    engine.create_tables(Base.metadata)  # Create tables if they don't exist
    orchestration = DatabaseOrchestration()
    
    with engine.get_session_context() as session:
        try:
            # First create a script for testing
            script_data = {
                "name": "Test Execution Script",
                "description": "Script for execution testing",
                "script_type": "python",
                "script_path": "/test/execution_script.py",
                "is_active": True,
                "version": "1.0.0"
            }
            
            script = orchestration.script_create(session, **script_data)
            print(f"✓ Created test script: {script.id}")
            
            # Create a simple workflow for execution
            workflow_data = {
                "name": "Execution Test Workflow",
                "description": "Simple workflow for execution testing",
                "nodes": [
                    {
                        "name": "start_node",
                        "node_type": "script",
                        "script_id": script.id,
                        "params": {"input": "test_execution"}
                    }
                ],
                "edges": []
            }
            
            workflow_result = orchestration.workflow_create(session, **workflow_data)
            workflow_id = workflow_result['workflow_id']
            print(f"✓ Created test workflow: {workflow_id}")
            
            # Test execution start
            execution_result = orchestration.execution_start(session, workflow_id)
            execution_id = execution_result['execution_id']
            print(f"✓ Started execution: {execution_id}")
            print(f"  Workflow ID: {execution_result['workflow_id']}")
            print(f"  Status: {execution_result['status']}")
            print(f"  Total nodes: {execution_result['total_nodes']}")
            print(f"  Pending nodes: {execution_result['pending_nodes']}")
            
            # Test multi-node workflow execution
            complex_workflow_data = {
                "name": "Complex Execution Test",
                "description": "Multi-node workflow for execution testing",
                "nodes": [
                    {
                        "name": "input_node",
                        "node_type": "script",
                        "script_id": script.id,
                        "params": {"stage": "input"}
                    },
                    {
                        "name": "process_node",
                        "node_type": "script", 
                        "script_id": script.id,
                        "params": {"stage": "process"}
                    },
                    {
                        "name": "output_node",
                        "node_type": "script",
                        "script_id": script.id,
                        "params": {"stage": "output"}
                    }
                ],
                "edges": [
                    {
                        "from_node": "input_node",
                        "to_node": "process_node",
                        "condition_type": "success"
                    },
                    {
                        "from_node": "process_node",
                        "to_node": "output_node",
                        "condition_type": "success"
                    }
                ]
            }
            
            complex_workflow = orchestration.workflow_create(session, **complex_workflow_data)
            complex_workflow_id = complex_workflow['workflow_id']
            print(f"✓ Created complex workflow: {complex_workflow_id}")
            
            complex_execution = orchestration.execution_start(session, complex_workflow_id)
            print(f"✓ Started complex execution: {complex_execution['execution_id']}")
            print(f"  Total nodes: {complex_execution['total_nodes']}")
            
            # session.commit() - handled by context manager
            
        except Exception as e:
            print(f"✗ Error: {e}")
            # session.rollback() - handled by context manager

def test_execution_cancel():
    """Test execution cancellation"""
    print("\n=== Testing Execution Cancel ===")
    
    config = get_sqlite_config(db_name='test_execution.db')
    engine = DatabaseEngine(config)
    engine.create_tables(Base.metadata)  # Create tables if they don't exist
    orchestration = DatabaseOrchestration()
    
    with engine.get_session_context() as session:
        try:
            # Get an existing workflow or create one
            workflows = orchestration.workflow_list(session, include_detail=False)
            if not workflows:
                # Create a workflow for cancellation test
                script_data = {
                    "name": "Cancel Test Script",
                    "script_type": "python",
                    "script_path": "/test/cancel_script.py",
                    "is_active": True
                }
                
                script = orchestration.script_create(session, **script_data)
                
                workflow_data = {
                    "name": "Cancel Test Workflow",
                    "description": "Workflow to test cancellation",
                    "nodes": [
                        {
                            "name": "cancel_test_node",
                            "node_type": "script",
                            "script_id": script.id,
                            "params": {"test": "cancellation"}
                        }
                    ],
                    "edges": []
                }
                
                workflow_result = orchestration.workflow_create(session, **workflow_data)
                workflow_id = workflow_result['workflow_id']
            else:
                workflow_id = workflows[0]['id']
            
            print(f"✓ Using workflow for cancel test: {workflow_id}")
            
            # Start execution
            execution_result = orchestration.execution_start(session, workflow_id)
            execution_id = execution_result['execution_id']
            print(f"✓ Started execution to cancel: {execution_id}")
            
            # Cancel the execution
            cancel_result = orchestration.cancel_execution(session, execution_id)
            print(f"✓ Cancelled execution: {cancel_result['execution_id']}")
            print(f"  Status: {cancel_result['status']}")
            print(f"  Cancelled at: {cancel_result['cancelled_at']}")
            
            # Try to cancel already cancelled execution
            try:
                orchestration.cancel_execution(session, execution_id)
                print("✗ Should have failed to cancel already cancelled execution")
            except BusinessLogicError as e:
                print(f"✓ Correctly failed to cancel cancelled execution: {e}")
            
            # Try to cancel non-existent execution
            try:
                orchestration.cancel_execution(session, "INVALID-EXECUTION-ID")
                print("✗ Should have failed for invalid execution ID")
            except BusinessLogicError as e:
                print(f"✓ Correctly failed for invalid ID: {e}")
                
            # session.commit() - handled by context manager
            
        except Exception as e:
            print(f"✗ Error: {e}")
            # session.rollback() - handled by context manager

def test_execution_get_and_list():
    """Test execution retrieval functions"""
    print("\n=== Testing Execution Get and List ===")
    
    config = get_sqlite_config(db_name='test_execution.db')
    engine = DatabaseEngine(config)
    engine.create_tables(Base.metadata)  # Create tables if they don't exist
    orchestration = DatabaseOrchestration()
    
    with engine.get_session_context() as session:
        try:
            # Get all executions
            all_executions = orchestration.execution_list(session)
            print(f"✓ Retrieved {len(all_executions)} executions")
            
            if all_executions:
                # Test get specific execution
                first_execution_id = all_executions[0]['id']
                execution_details = orchestration.execution_get(session, first_execution_id)
                print(f"✓ Retrieved execution details: {execution_details['id']}")
                print(f"  Workflow ID: {execution_details['workflow_id']}")
                print(f"  Status: {execution_details['status']}")
                print(f"  Started: {execution_details.get('started_at', 'N/A')}")
                
                # Test execution exists
                exists = orchestration.execution_exists(session, first_execution_id)
                print(f"✓ Execution exists check: {exists}")
                
                # Test non-existent execution
                exists_invalid = orchestration.execution_exists(session, "INVALID-ID")
                print(f"✓ Invalid execution exists check: {exists_invalid}")
                
                # Test get execution status
                status = orchestration.execution_get_status(session, first_execution_id)
                print(f"✓ Execution status: {status}")
                
                # Test get execution result
                result = orchestration.execution_get_result(session, first_execution_id)
                print(f"✓ Execution result retrieved: {type(result)}")
            
            # Test count
            execution_count = orchestration.execution_count(session)
            print(f"✓ Total execution count: {execution_count}")
            
        except Exception as e:
            print(f"✗ Error: {e}")

def test_execution_filter():
    """Test execution filtering"""
    print("\n=== Testing Execution Filter ===")
    
    config = get_sqlite_config(db_name='test_execution.db')
    engine = DatabaseEngine(config)
    engine.create_tables(Base.metadata)  # Create tables if they don't exist
    orchestration = DatabaseOrchestration()
    
    with engine.get_session_context() as session:
        try:
            # Create multiple executions for filtering tests
            workflows = orchestration.workflow_list(session, include_detail=False)
            
            if workflows:
                # Create several executions
                execution_ids = []
                for i, workflow in enumerate(workflows[:3]):  # Use up to 3 workflows
                    execution = orchestration.execution_start(session, workflow['id'])
                    execution_ids.append(execution['execution_id'])
                    print(f"✓ Created test execution {i+1}: {execution['execution_id']}")
                
                # Cancel one execution for filtering
                if len(execution_ids) > 1:
                    cancel_result = orchestration.cancel_execution(session, execution_ids[1])
                    print(f"✓ Cancelled execution for filter test: {execution_ids[1]}")
                
                # Test filter by status
                pending_filter = {'status': 'pending'}
                pending_executions = orchestration.execution_filter(session, pending_filter)
                print(f"✓ Found {len(pending_executions)} pending executions")
                
                cancelled_filter = {'status': 'cancelled'}
                cancelled_executions = orchestration.execution_filter(session, cancelled_filter)
                print(f"✓ Found {len(cancelled_executions)} cancelled executions")
                
                # Test filter by workflow_id
                if workflows:
                    workflow_filter = {'workflow_id': workflows[0]['id']}
                    workflow_executions = orchestration.execution_filter(session, workflow_filter)
                    print(f"✓ Found {len(workflow_executions)} executions for specific workflow")
                
            # session.commit() - handled by context manager
            
        except Exception as e:
            print(f"✗ Error: {e}")
            # session.rollback() - handled by context manager

def test_execution_results_combination():
    """Test _combine_execution_results functionality"""
    print("\n=== Testing Execution Results Combination ===")
    
    config = get_sqlite_config(db_name='test_execution.db')
    engine = DatabaseEngine(config)
    engine.create_tables(Base.metadata)  # Create tables if they don't exist
    orchestration = DatabaseOrchestration()
    
    with engine.get_session_context() as session:
        try:
            # Create a workflow with multiple nodes
            script_data = {
                "name": "Results Test Script",
                "script_type": "python", 
                "script_path": "/test/results_script.py",
                "is_active": True
            }
            
            script = orchestration.script_create(session, **script_data)
            
            workflow_data = {
                "name": "Results Combination Test",
                "description": "Test workflow for results combination",
                "nodes": [
                    {
                        "name": "step_1",
                        "node_type": "script",
                        "script_id": script.id,
                        "params": {"step": 1}
                    },
                    {
                        "name": "step_2",
                        "node_type": "script", 
                        "script_id": script.id,
                        "params": {"step": 2}
                    },
                    {
                        "name": "step_3",
                        "node_type": "script",
                        "script_id": script.id,
                        "params": {"step": 3}
                    }
                ],
                "edges": [
                    {
                        "from_node": "step_1",
                        "to_node": "step_2",
                        "condition_type": "success"
                    },
                    {
                        "from_node": "step_2",
                        "to_node": "step_3", 
                        "condition_type": "success"
                    }
                ]
            }
            
            workflow_result = orchestration.workflow_create(session, **workflow_data)
            workflow_id = workflow_result['workflow_id']
            print(f"✓ Created results test workflow: {workflow_id}")
            
            # Start execution
            execution = orchestration.execution_start(session, workflow_id)
            execution_id = execution['execution_id']
            print(f"✓ Started execution: {execution_id}")
            
            # Test the internal _combine_execution_results method
            combined_results = orchestration._combine_execution_results(session, execution_id)
            print(f"✓ Combined execution results")
            print(f"  Execution ID: {combined_results['execution_id']}")
            print(f"  Workflow ID: {combined_results['workflow_id']}")
            print(f"  Status: {combined_results['execution_status']}")
            print(f"  Total nodes: {combined_results['summary']['total_nodes']}")
            print(f"  Node results: {len(combined_results['node_results'])} entries")
            
            # Show node results structure
            for node_name, node_result in combined_results['node_results'].items():
                print(f"    {node_name}: {node_result['status']}")
            
            # session.commit() - handled by context manager
            
        except Exception as e:
            print(f"✗ Error: {e}")
            # session.rollback() - handled by context manager

def test_execution_validation():
    """Test execution validation and error handling"""
    print("\n=== Testing Execution Validation ===")
    
    config = get_sqlite_config(db_name='test_execution.db')
    engine = DatabaseEngine(config)
    engine.create_tables(Base.metadata)  # Create tables if they don't exist
    orchestration = DatabaseOrchestration()
    
    with engine.get_session_context() as session:
        try:
            # Test starting execution with invalid workflow ID
            try:
                orchestration.execution_start(session, "INVALID-WORKFLOW-ID")
                print("✗ Should have failed for invalid workflow ID")
            except BusinessLogicError as e:
                print(f"✓ Correctly failed for invalid workflow ID: {e}")
            
            # Test getting invalid execution
            try:
                orchestration.execution_get(session, "INVALID-EXECUTION-ID")
                print("✗ Should have failed for invalid execution ID")
            except BusinessLogicError as e:
                print(f"✓ Correctly failed for invalid execution ID: {e}")
            
            # Test getting status of invalid execution
            try:
                orchestration.execution_get_status(session, "INVALID-EXECUTION-ID")
                print("✗ Should have failed for invalid execution ID")
            except Exception as e:
                print(f"✓ Correctly failed for invalid execution ID: {type(e).__name__}")
            
            # Test getting result of invalid execution
            try:
                orchestration.execution_get_result(session, "INVALID-EXECUTION-ID")
                print("✗ Should have failed for invalid execution ID")
            except Exception as e:
                print(f"✓ Correctly failed for invalid execution ID: {type(e).__name__}")
            
            # session.commit() - handled by context manager
            
        except Exception as e:
            print(f"✗ Error: {e}")
            # session.rollback() - handled by context manager

def test_execution_lifecycle():
    """Test complete execution lifecycle"""
    print("\n=== Testing Complete Execution Lifecycle ===")
    
    config = get_sqlite_config(db_name='test_execution.db')
    engine = DatabaseEngine(config)
    engine.create_tables(Base.metadata)  # Create tables if they don't exist
    orchestration = DatabaseOrchestration()
    
    with engine.get_session_context() as session:
        try:
            # Create script
            script_data = {
                "name": "Lifecycle Test Script",
                "description": "Script for lifecycle testing",
                "script_type": "python",
                "script_path": "/test/lifecycle_script.py",
                "is_active": True
            }
            
            script = orchestration.script_create(session, **script_data)
            print(f"✓ Created lifecycle test script: {script.id}")
            
            # Create workflow
            workflow_data = {
                "name": "Lifecycle Test Workflow",
                "description": "Complete lifecycle test",
                "nodes": [
                    {
                        "name": "init_node",
                        "node_type": "script",
                        "script_id": script.id,
                        "params": {"phase": "initialization"}
                    },
                    {
                        "name": "main_node",
                        "node_type": "script",
                        "script_id": script.id,
                        "params": {"phase": "main_processing"}
                    },
                    {
                        "name": "cleanup_node", 
                        "node_type": "script",
                        "script_id": script.id,
                        "params": {"phase": "cleanup"}
                    }
                ],
                "edges": [
                    {
                        "from_node": "init_node",
                        "to_node": "main_node",
                        "condition_type": "success"
                    },
                    {
                        "from_node": "main_node",
                        "to_node": "cleanup_node",
                        "condition_type": "success"
                    }
                ]
            }
            
            workflow = orchestration.workflow_create(session, **workflow_data)
            workflow_id = workflow['workflow_id']
            print(f"✓ Created lifecycle workflow: {workflow_id}")
            
            # Start execution
            execution = orchestration.execution_start(session, workflow_id)
            execution_id = execution['execution_id']
            print(f"✓ Started execution: {execution_id}")
            print(f"  Initial status: {execution['status']}")
            
            # Check execution details
            execution_details = orchestration.execution_get(session, execution_id)
            print(f"✓ Retrieved execution details")
            print(f"  Pending nodes: {execution_details.get('pending_nodes', 'N/A')}")
            print(f"  Executed nodes: {execution_details.get('executed_nodes', 'N/A')}")
            
            # Get combined results
            results = orchestration._combine_execution_results(session, execution_id)
            print(f"✓ Retrieved combined results")
            print(f"  Summary: {results['summary']}")
            
            # Cancel execution to test cancellation in lifecycle
            cancel_result = orchestration.cancel_execution(session, execution_id)
            print(f"✓ Cancelled execution in lifecycle test")
            print(f"  Final status: {cancel_result['status']}")
            
            # session.commit() - handled by context manager
            
        except Exception as e:
            print(f"✗ Error: {e}")
            # session.rollback() - handled by context manager

def run_all_execution_tests():
    """Run all execution tests"""
    print("Starting Execution Function Tests")
    print("=" * 50)
    
    test_execution_start()
    test_execution_cancel()
    test_execution_get_and_list()
    test_execution_filter()
    test_execution_results_combination()
    test_execution_validation()
    test_execution_lifecycle()
    
    print("\n" + "=" * 50)
    print("Execution tests completed!")

if __name__ == "__main__":
    run_all_execution_tests()
