#!/usr/bin/env python3
"""
Execution status method'unun string döndürdüğünü test eder
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from miniflow.database_manager.config import get_sqlite_config
from miniflow.database_manager.engine import DatabaseEngine
from miniflow.database_manager.orchestration import DatabaseOrchestration
from miniflow.database_manager.models import Base, ScriptType
import uuid

def test_execution_status_string():
    """Execution status method'unun string döndürdüğünü test eder"""
    
    print("=" * 60)
    print("EXECUTION STATUS STRING TEST")
    print("=" * 60)
    
    # Database setup
    config = get_sqlite_config(db_name='test_execution_status.db')
    engine = DatabaseEngine(config)
    engine.create_tables(Base.metadata)
    orchestration = DatabaseOrchestration()
    
    with engine.get_session_context() as session:
        
        # Test workflow ve script oluştur
        unique_id = uuid.uuid4().hex[:8]
        
        # Script oluştur
        script_data = {
            'name': f'Test Script {unique_id}',
            'description': 'Test script for status testing',
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
            'description': 'Test workflow for status testing',
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
        
        # Execution başlat
        execution_start = orchestration.execution_start(session, workflow_id)
        execution_id = execution_start['execution_id']
        
        print("\n1. EXECUTION GET STATUS (PENDING):")
        print("-" * 30)
        status = orchestration.execution_get_status(session, execution_id)
        print(f"Return Type: {type(status)}")
        print(f"Return Value: {status}")
        print(f"Is String: {isinstance(status, str)}")
        
        # Execution iptal et
        orchestration.cancel_execution(session, execution_id)
        
        print("\n2. EXECUTION GET STATUS (CANCELLED):")
        print("-" * 30)
        status = orchestration.execution_get_status(session, execution_id)
        print(f"Return Type: {type(status)}")
        print(f"Return Value: {status}")
        print(f"Is String: {isinstance(status, str)}")
        
        # Yeni execution başlat ve farklı durumları test et
        execution_start2 = orchestration.execution_start(session, workflow_id)
        execution_id2 = execution_start2['execution_id']
        
        print("\n3. EXECUTION GET STATUS (PENDING - YENİ):")
        print("-" * 30)
        status = orchestration.execution_get_status(session, execution_id2)
        print(f"Return Type: {type(status)}")
        print(f"Return Value: {status}")
        print(f"Is String: {isinstance(status, str)}")
        
        # Status değerlerini karşılaştır
        print("\n4. STATUS DEĞERLERİ KARŞILAŞTIRMASI:")
        print("-" * 30)
        status1 = orchestration.execution_get_status(session, execution_id)   # cancelled
        status2 = orchestration.execution_get_status(session, execution_id2)  # pending
        print(f"Status 1 (Cancelled): {status1} (Type: {type(status1)})")
        print(f"Status 2 (Pending): {status2} (Type: {type(status2)})")
        print(f"Both are strings: {isinstance(status1, str) and isinstance(status2, str)}")

if __name__ == "__main__":
    test_execution_status_string()
