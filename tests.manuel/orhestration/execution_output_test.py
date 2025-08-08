#!/usr/bin/env python3
"""
Execution fonksiyonlarının çıktı formatlarını test eder
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from miniflow.database_manager.config import get_sqlite_config
from miniflow.database_manager.engine import DatabaseEngine
from miniflow.database_manager.orchestration import DatabaseOrchestration
from miniflow.database_manager.models import Base, ScriptType
import uuid

def test_execution_outputs():
    """Execution fonksiyonlarının çıktı formatlarını test eder"""
    
    print("=" * 60)
    print("EXECUTION FONKSİYONLARININ ÇIKTI FORMATLARI")
    print("=" * 60)
    
    # Database setup
    config = get_sqlite_config(db_name='test_execution_outputs.db')
    engine = DatabaseEngine(config)
    engine.create_tables(Base.metadata)
    orchestration = DatabaseOrchestration()
    
    with engine.get_session_context() as session:
        
        # Test workflow ve script oluştur
        unique_id = uuid.uuid4().hex[:8]
        
        # Script oluştur
        script_data = {
            'name': f'Test Script {unique_id}',
            'description': 'Test script for execution testing',
            'language': ScriptType.PYTHON,
            'type': 'python',
            'script_path': '/path/to/test_script.py',
            'input_params': {'param1': 'string'},
            'output_params': {'result': 'string'},
            'test_status': 'untested'
        }
        script = orchestration.script_create(session, **script_data)
        
        # Workflow oluştur
        workflow_data = {
            'name': f'Test Workflow {unique_id}',
            'description': 'Test workflow for execution testing',
            'nodes': [
                {
                    'name': 'test_node_1',
                    'script_id': script['id'],
                    'params': {'param1': 'value1'},
                    'max_retries': 3,
                    'timeout_seconds': 300
                }
            ],
            'edges': []
        }
        workflow = orchestration.workflow_create(session, **workflow_data)
        workflow_id = workflow['workflow_id']
        
        print("\n1. EXECUTION START ÇIKTISI:")
        print("-" * 30)
        execution_start = orchestration.execution_start(session, workflow_id)
        print(f"Return Type: {type(execution_start)}")
        print(f"Return Value: {execution_start}")
        
        execution_id = execution_start['execution_id']
        
        print("\n2. EXECUTION GET ÇIKTISI:")
        print("-" * 30)
        execution_get = orchestration.execution_get(session, execution_id)
        print(f"Return Type: {type(execution_get)}")
        print(f"Return Value: {execution_get}")
        
        print("\n3. EXECUTION LIST ÇIKTISI:")
        print("-" * 30)
        execution_list = orchestration.execution_list(session)
        print(f"Return Type: {type(execution_list)}")
        print(f"List Length: {len(execution_list)}")
        print(f"First Item Type: {type(execution_list[0]) if execution_list else 'None'}")
        if execution_list:
            print(f"First Item: {execution_list[0]}")
        
        print("\n4. EXECUTION COUNT ÇIKTISI:")
        print("-" * 30)
        execution_count = orchestration.execution_count(session)
        print(f"Return Type: {type(execution_count)}")
        print(f"Return Value: {execution_count}")
        
        print("\n5. EXECUTION EXISTS ÇIKTISI:")
        print("-" * 30)
        execution_exists = orchestration.execution_exists(session, execution_id)
        print(f"Return Type: {type(execution_exists)}")
        print(f"Return Value: {execution_exists}")
        
        print("\n6. EXECUTION FILTER ÇIKTISI:")
        print("-" * 30)
        execution_filter = orchestration.execution_filter(session, {'workflow_id': workflow_id})
        print(f"Return Type: {type(execution_filter)}")
        print(f"List Length: {len(execution_filter)}")
        print(f"First Item Type: {type(execution_filter[0]) if execution_filter else 'None'}")
        if execution_filter:
            print(f"First Item: {execution_filter[0]}")
        
        print("\n7. EXECUTION GET STATUS ÇIKTISI:")
        print("-" * 30)
        execution_status = orchestration.execution_get_status(session, execution_id)
        print(f"Return Type: {type(execution_status)}")
        print(f"Return Value: {execution_status}")
        
        print("\n8. EXECUTION GET RESULT ÇIKTISI:")
        print("-" * 30)
        execution_result = orchestration.execution_get_result(session, execution_id)
        print(f"Return Type: {type(execution_result)}")
        print(f"Return Value: {execution_result}")
        
        print("\n9. EXECUTION CANCEL ÇIKTISI:")
        print("-" * 30)
        execution_cancel = orchestration.cancel_execution(session, execution_id)
        print(f"Return Type: {type(execution_cancel)}")
        print(f"Return Value: {execution_cancel}")

if __name__ == "__main__":
    test_execution_outputs()
