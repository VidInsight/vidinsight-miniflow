#!/usr/bin/env python3
"""
Script fonksiyonlarının çıktı formatlarını test eder
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from miniflow.database_manager.config import get_sqlite_config
from miniflow.database_manager.engine import DatabaseEngine
from miniflow.database_manager.orchestration import DatabaseOrchestration
from miniflow.database_manager.models import Base, ScriptType
import uuid

def test_script_outputs():
    """Script fonksiyonlarının çıktı formatlarını test eder"""
    
    print("=" * 60)
    print("SCRIPT FONKSİYONLARININ ÇIKTI FORMATLARI")
    print("=" * 60)
    
    # Database setup
    config = get_sqlite_config(db_name='test_script_outputs.db')
    engine = DatabaseEngine(config)
    engine.create_tables(Base.metadata)
    orchestration = DatabaseOrchestration()
    
    with engine.get_session_context() as session:
        
        # Test script oluştur
        unique_id = uuid.uuid4().hex[:8]
        script_data = {
            'name': f'Test Script {unique_id}',
            'description': 'Test script for output format testing',
            'language': ScriptType.PYTHON,
            'type': 'python',
            'script_path': '/path/to/test_script.py',
            'input_params': {'param1': 'string', 'param2': 'number'},
            'output_params': {'result': 'string'},
            'test_status': 'untested'
        }
        
        print("\n1. SCRIPT CREATE ÇIKTISI:")
        print("-" * 30)
        created_script = orchestration.script_create(session, **script_data)
        print(f"Return Type: {type(created_script)}")
        print(f"Return Value: {created_script}")
        if hasattr(created_script, 'to_dict'):
            print(f"to_dict(): {created_script.to_dict()}")
        
        script_id = created_script['id']
        
        print("\n2. SCRIPT GET ÇIKTISI:")
        print("-" * 30)
        retrieved_script = orchestration.script_get(session, script_id)
        print(f"Return Type: {type(retrieved_script)}")
        print(f"Return Value: {retrieved_script}")
        if isinstance(retrieved_script, dict):
            print(f"Dict format: {retrieved_script}")
        elif hasattr(retrieved_script, 'to_dict'):
            print(f"to_dict(): {retrieved_script.to_dict()}")
        
        print("\n3. SCRIPT LIST ÇIKTISI (GÜNCELLENMİŞ):")
        print("-" * 30)
        script_list = orchestration.script_list(session)
        print(f"Return Type: {type(script_list)}")
        print(f"List Length: {len(script_list)}")
        print(f"First Item Type: {type(script_list[0]) if script_list else 'None'}")
        if script_list:
            print(f"First Item: {script_list[0]}")
        
        print("\n4. SCRIPT COUNT ÇIKTISI:")
        print("-" * 30)
        script_count = orchestration.script_count(session)
        print(f"Return Type: {type(script_count)}")
        print(f"Return Value: {script_count}")
        
        print("\n5. SCRIPT EXISTS ÇIKTISI:")
        print("-" * 30)
        script_exists = orchestration.script_exists(session, script_id)
        print(f"Return Type: {type(script_exists)}")
        print(f"Return Value: {script_exists}")
        
        print("\n6. SCRIPT FILTER ÇIKTISI (GÜNCELLENMİŞ):")
        print("-" * 30)
        script_filter = orchestration.script_filter(session, {'language': ScriptType.PYTHON})
        print(f"Return Type: {type(script_filter)}")
        print(f"List Length: {len(script_filter)}")
        print(f"First Item Type: {type(script_filter[0]) if script_filter else 'None'}")
        if script_filter:
            print(f"First Item: {script_filter[0]}")
        
        print("\n7. SCRIPT UPDATE ÇIKTISI:")
        print("-" * 30)
        update_data = {'description': 'Updated description for testing'}
        updated_script = orchestration.script_update(session, script_id, **update_data)
        print(f"Return Type: {type(updated_script)}")
        print(f"Return Value: {updated_script}")
        if hasattr(updated_script, 'to_dict'):
            print(f"to_dict(): {updated_script.to_dict()}")
        
        print("\n8. SCRIPT DELETE ÇIKTISI:")
        print("-" * 30)
        deleted_script = orchestration.script_delete(session, script_id)
        print(f"Return Type: {type(deleted_script)}")
        print(f"Return Value: {deleted_script}")
        if hasattr(deleted_script, 'to_dict'):
            print(f"to_dict(): {deleted_script.to_dict()}")

if __name__ == "__main__":
    test_script_outputs()
