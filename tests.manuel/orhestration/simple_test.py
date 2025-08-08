"""
Simple orchestration test to verify basic functionality
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

def test_basic_workflow():
    print("=== Simple Workflow Test ===")
    
    # Use unique database for this test
    db_name = f'simple_test_{int(time.time())}.db'
    config = get_sqlite_config(db_name=db_name)
    engine = DatabaseEngine(config)
    engine.create_tables(Base.metadata)
    orchestration = DatabaseOrchestration()
    
    with engine.get_session_context() as session:
        try:
            # Create a script first
            script_data = {
                "name": f"Test Script {uuid.uuid4().hex[:8]}",
                "description": "Simple test script",
                "language": ScriptType.PYTHON,
                "script_path": "/test/simple_script.py"
            }
            
            script = orchestration.script_create(session, **script_data)
            print(f"✓ Script created: {script.id} - {script.name}")
            
            # Create a simple workflow
            workflow_data = {
                "name": f"Simple Workflow {uuid.uuid4().hex[:8]}",
                "description": "Simple test workflow",
                "nodes": [
                    {
                        "name": "simple_node",
                        "script_id": script.id,
                        "params": {"test": "value"}
                    }
                ],
                "edges": []
            }
            
            workflow = orchestration.workflow_create(session, **workflow_data)
            print(f"✓ Workflow created: {workflow['workflow_id']}")
            print(f"  Nodes: {len(workflow['nodes'])}")
            
            # Get the workflow
            retrieved = orchestration.workflow_get(session, workflow['workflow_id'])
            print(f"✓ Retrieved workflow: {retrieved['name']}")
            
            # Start execution
            execution = orchestration.execution_start(session, workflow['workflow_id'])
            print(f"✓ Execution started: {execution['execution_id']}")
            print(f"  Status: {execution['status']}")
            print(f"  Total nodes: {execution['total_nodes']}")
            
            # Get execution status
            status = orchestration.execution_get_status(session, execution['execution_id'])
            print(f"✓ Execution status: {status}")
            
            # Cancel execution
            cancel_result = orchestration.cancel_execution(session, execution['execution_id'])
            print(f"✓ Execution cancelled: {cancel_result['status']}")
            
            print("✓ All basic tests passed!")
            
        except Exception as e:
            print(f"✗ Error: {e}")
            import traceback
            traceback.print_exc()

def test_script_operations():
    print("\n=== Script Operations Test ===")
    
    db_name = f'script_test_{int(time.time())}.db'
    config = get_sqlite_config(db_name=db_name)
    engine = DatabaseEngine(config)
    engine.create_tables(Base.metadata)
    orchestration = DatabaseOrchestration()
    
    with engine.get_session_context() as session:
        try:
            # Create scripts
            script1 = {
                "name": f"Python Script {uuid.uuid4().hex[:8]}",
                "description": "Python test script",
                "language": ScriptType.PYTHON,
                "script_path": "/test/python_script.py"
            }
            
            script2 = {
                "name": f"Python Script 2 {uuid.uuid4().hex[:8]}",
                "description": "Second Python test script", 
                "language": ScriptType.PYTHON,
                "script_path": "/test/python_script2.py"
            }
            
            s1 = orchestration.script_create(session, **script1)
            s2 = orchestration.script_create(session, **script2)
            
            print(f"✓ Created Python script: {s1.id}")
            print(f"✓ Created second Python script: {s2.id}")
            
            # List scripts
            all_scripts = orchestration.script_list(session)
            print(f"✓ Total scripts: {len(all_scripts)}")
            
            # Filter scripts
            python_scripts = orchestration.script_filter(session, {'language': ScriptType.PYTHON})
            print(f"✓ Python scripts: {len(python_scripts)}")
            
            # Update script
            updated = orchestration.script_update(session, s1.id, description="Updated description")
            print(f"✓ Updated script description: {updated.description}")
            
            # Get script by ID
            retrieved = orchestration.script_get(session, s1.id)
            print(f"✓ Retrieved script: {retrieved.name}")
            
            print("✓ All script tests passed!")
            
        except Exception as e:
            print(f"✗ Error: {e}")
            import traceback
            traceback.print_exc()

def main():
    print("🚀 SIMPLE ORCHESTRATION TESTS")
    print("=" * 40)
    
    test_basic_workflow()
    test_script_operations()
    
    print("\n" + "=" * 40)
    print("Tests completed!")

if __name__ == "__main__":
    main()
