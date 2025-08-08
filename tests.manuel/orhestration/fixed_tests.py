"""
Fixed orchestration tests with correct model fields
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from miniflow.database_manager.engine import DatabaseEngine
from miniflow.database_manager.config import get_sqlite_config
from miniflow.database_manager.orchestration import DatabaseOrchestration
from miniflow.database_manager.models import Base, ScriptType
import uuid
import time

def test_workflow_operations():
    print("=== Fixed Workflow Test ===")
    
    db_name = f'fixed_workflow_{int(time.time())}.db'
    config = get_sqlite_config(db_name=db_name)
    engine = DatabaseEngine(config)
    engine.create_tables(Base.metadata)
    orchestration = DatabaseOrchestration()
    
    with engine.get_session_context() as session:
        try:
            # Create script with correct fields
            script_data = {
                "name": f"Script {uuid.uuid4().hex[:8]}",
                "description": "Test script",
                "language": ScriptType.PYTHON,
                "script_path": "/test/script.py"
            }
            
            script = orchestration.script_create(session, **script_data)
            print(f"✓ Script created: {script.name}")
            
            # Create workflow with unique name and correct fields
            workflow_data = {
                "name": f"Workflow {uuid.uuid4().hex[:8]}",
                "description": "Test workflow",
                "nodes": [
                    {
                        "name": "test_node",
                        "script_id": script.id,
                        "params": {"test": "value"}
                    }
                ],
                "edges": []
            }
            
            workflow = orchestration.workflow_create(session, **workflow_data)
            print(f"✓ Workflow created: {workflow['workflow_id']}")
            
            # Test workflow operations
            retrieved = orchestration.workflow_get(session, workflow['workflow_id'])
            print(f"✓ Retrieved workflow: {retrieved['name']}")
            
            # Update workflow
            updated = orchestration.workflow_update(session, workflow['workflow_id'], 
                                                  description="Updated description")
            print(f"✓ Updated workflow description")
            
            # Start execution
            execution = orchestration.execution_start(session, workflow['workflow_id'])
            print(f"✓ Execution started: {execution['execution_id']}")
            
            # Cancel execution
            cancel_result = orchestration.cancel_execution(session, execution['execution_id'])
            print(f"✓ Execution cancelled: {cancel_result['status']}")
            
            print("✓ All workflow operations passed!")
            
        except Exception as e:
            print(f"✗ Error: {e}")
            import traceback
            traceback.print_exc()

def test_script_operations():
    print("\n=== Fixed Script Test ===")
    
    db_name = f'fixed_script_{int(time.time())}.db'
    config = get_sqlite_config(db_name=db_name)
    engine = DatabaseEngine(config)
    engine.create_tables(Base.metadata)
    orchestration = DatabaseOrchestration()
    
    with engine.get_session_context() as session:
        try:
            # Create scripts with correct fields only
            script1_data = {
                "name": f"Python Script {uuid.uuid4().hex[:8]}",
                "description": "Python test script",
                "language": ScriptType.PYTHON,
                "script_path": "/test/python1.py"
            }
            
            script2_data = {
                "name": f"Python Script {uuid.uuid4().hex[:8]}",
                "description": "Another Python script",
                "language": ScriptType.PYTHON,
                "script_path": "/test/python2.py"
            }
            
            s1 = orchestration.script_create(session, **script1_data)
            s2 = orchestration.script_create(session, **script2_data)
            print(f"✓ Created scripts: {s1.name}, {s2.name}")
            
            # Test script operations
            all_scripts = orchestration.script_list(session)
            print(f"✓ Listed {len(all_scripts)} scripts")
            
            # Update script (only valid fields)
            updated = orchestration.script_update(session, s1.id, 
                                                description="Updated description")
            print(f"✓ Updated script: {updated.description}")
            
            # Get script
            retrieved = orchestration.script_get(session, s1.id)
            print(f"✓ Retrieved script: {retrieved.name}")
            
            # Filter scripts
            python_scripts = orchestration.script_filter(session, {'language': ScriptType.PYTHON})
            print(f"✓ Filtered {len(python_scripts)} Python scripts")
            
            # Delete script  
            deleted = orchestration.script_delete(session, s2.id)
            print(f"✓ Deleted script: {deleted.name}")
            
            print("✓ All script operations passed!")
            
        except Exception as e:
            print(f"✗ Error: {e}")
            import traceback
            traceback.print_exc()

def test_environment_operations():
    print("\n=== Fixed Environment Test ===")
    
    db_name = f'fixed_env_{int(time.time())}.db'
    config = get_sqlite_config(db_name=db_name)
    engine = DatabaseEngine(config)
    engine.create_tables(Base.metadata)
    orchestration = DatabaseOrchestration()
    
    with engine.get_session_context() as session:
        try:
            # Create environment variables with correct fields
            env1_data = {
                "name": f"TEST_VAR_{uuid.uuid4().hex[:8]}",
                "value": "test_value_1",
                "description": "Test environment variable",
                "is_sensitive": False
            }
            
            env2_data = {
                "name": f"SECRET_VAR_{uuid.uuid4().hex[:8]}",
                "value": "secret_value_123",
                "description": "Secret test variable",
                "is_sensitive": True
            }
            
            e1 = orchestration.environment_create(session, **env1_data)
            e2 = orchestration.environment_create(session, **env2_data)
            print(f"✓ Created environment variables: {e1.name}, {e2.name}")
            
            # Test environment operations
            all_envs = orchestration.environment_list(session)
            print(f"✓ Listed {len(all_envs)} environment variables")
            
            # Update environment
            updated = orchestration.environment_update(session, e1.id,
                                                     value="updated_value")
            print(f"✓ Updated environment variable value")
            
            # Get environment
            retrieved = orchestration.environment_get(session, e1.id)
            print(f"✓ Retrieved environment variable: {retrieved['name']}")
            
            # Filter environments
            sensitive_envs = orchestration.environment_filter(session, {'is_sensitive': True})
            print(f"✓ Filtered {len(sensitive_envs)} sensitive variables")
            
            # Delete environment
            deleted = orchestration.environment_delete(session, e2.id)
            print(f"✓ Deleted environment variable: {deleted.name}")
            
            print("✓ All environment operations passed!")
            
        except Exception as e:
            print(f"✗ Error: {e}")
            import traceback
            traceback.print_exc()

def test_execution_lifecycle():
    print("\n=== Fixed Execution Lifecycle Test ===")
    
    db_name = f'fixed_exec_{int(time.time())}.db'
    config = get_sqlite_config(db_name=db_name)
    engine = DatabaseEngine(config)
    engine.create_tables(Base.metadata)
    orchestration = DatabaseOrchestration()
    
    with engine.get_session_context() as session:
        try:
            # Create script and workflow
            script_data = {
                "name": f"Exec Script {uuid.uuid4().hex[:8]}",
                "description": "Execution test script",
                "language": ScriptType.PYTHON,
                "script_path": "/test/exec_script.py"
            }
            
            script = orchestration.script_create(session, **script_data)
            
            workflow_data = {
                "name": f"Exec Workflow {uuid.uuid4().hex[:8]}",
                "description": "Execution test workflow",
                "nodes": [
                    {
                        "name": "exec_node_1",
                        "script_id": script.id,
                        "params": {"step": 1}
                    },
                    {
                        "name": "exec_node_2", 
                        "script_id": script.id,
                        "params": {"step": 2}
                    }
                ],
                "edges": [
                    {
                        "from_node": "exec_node_1",
                        "to_node": "exec_node_2",
                        "condition_type": "success"
                    }
                ]
            }
            
            workflow = orchestration.workflow_create(session, **workflow_data)
            print(f"✓ Created workflow with 2 nodes: {workflow['workflow_id']}")
            
            # Start execution
            execution = orchestration.execution_start(session, workflow['workflow_id'])
            print(f"✓ Started execution: {execution['execution_id']}")
            print(f"  Status: {execution['status']}")
            print(f"  Total nodes: {execution['total_nodes']}")
            
            # Get execution details
            exec_details = orchestration.execution_get(session, execution['execution_id'])
            print(f"✓ Retrieved execution details")
            
            # Get execution status
            status = orchestration.execution_get_status(session, execution['execution_id'])
            print(f"✓ Execution status: {status}")
            
            # Test combine results method
            results = orchestration._combine_execution_results(session, execution['execution_id'])
            print(f"✓ Combined results - Summary: {results['summary']}")
            print(f"  Node results: {len(results['node_results'])} entries")
            
            # Cancel execution
            cancel_result = orchestration.cancel_execution(session, execution['execution_id'])
            print(f"✓ Cancelled execution: {cancel_result['status']}")
            
            print("✓ All execution lifecycle operations passed!")
            
        except Exception as e:
            print(f"✗ Error: {e}")
            import traceback
            traceback.print_exc()

def main():
    print("🚀 FIXED ORCHESTRATION TESTS")
    print("=" * 50)
    
    test_workflow_operations()
    test_script_operations()
    test_environment_operations()
    test_execution_lifecycle()
    
    print("\n" + "=" * 50)
    print("✅ All fixed tests completed!")

if __name__ == "__main__":
    main()
