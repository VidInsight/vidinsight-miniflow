#!/usr/bin/env python3
"""
Environment fonksiyonlarının çıktı formatlarını test eder
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from miniflow.database_manager.config import get_sqlite_config
from miniflow.database_manager.engine import DatabaseEngine
from miniflow.database_manager.orchestration import DatabaseOrchestration
from miniflow.database_manager.models import Base
import uuid

def test_environment_outputs():
    """Environment fonksiyonlarının çıktı formatlarını test eder"""
    
    print("=" * 60)
    print("ENVIRONMENT FONKSİYONLARININ ÇIKTI FORMATLARI")
    print("=" * 60)
    
    # Database setup
    config = get_sqlite_config(db_name='test_environment_outputs.db')
    engine = DatabaseEngine(config)
    engine.create_tables(Base.metadata)
    orchestration = DatabaseOrchestration()
    
    with engine.get_session_context() as session:
        
        # Test environment oluştur
        unique_id = uuid.uuid4().hex[:8]
        env_data = {
            'name': f'TEST_ENV_{unique_id}',
            'value': 'test_value_123',
            'description': 'Test environment variable for output format testing',
            'is_sensitive': False
        }
        
        print("\n1. ENVIRONMENT CREATE ÇIKTISI:")
        print("-" * 30)
        created_env = orchestration.environment_create(session, **env_data)
        print(f"Return Type: {type(created_env)}")
        print(f"Return Value: {created_env}")
        
        env_id = created_env['id']
        
        print("\n2. ENVIRONMENT GET ÇIKTISI:")
        print("-" * 30)
        retrieved_env = orchestration.environment_get(session, env_id)
        print(f"Return Type: {type(retrieved_env)}")
        print(f"Return Value: {retrieved_env}")
        
        print("\n3. ENVIRONMENT LIST ÇIKTISI:")
        print("-" * 30)
        env_list = orchestration.environment_list(session)
        print(f"Return Type: {type(env_list)}")
        print(f"List Length: {len(env_list)}")
        print(f"First Item Type: {type(env_list[0]) if env_list else 'None'}")
        if env_list:
            print(f"First Item: {env_list[0]}")
        
        print("\n4. ENVIRONMENT COUNT ÇIKTISI:")
        print("-" * 30)
        env_count = orchestration.environment_count(session)
        print(f"Return Type: {type(env_count)}")
        print(f"Return Value: {env_count}")
        
        print("\n5. ENVIRONMENT EXISTS ÇIKTISI:")
        print("-" * 30)
        env_exists = orchestration.environment_exists(session, env_id)
        print(f"Return Type: {type(env_exists)}")
        print(f"Return Value: {env_exists}")
        
        print("\n6. ENVIRONMENT FILTER ÇIKTISI:")
        print("-" * 30)
        env_filter = orchestration.environment_filter(session, {'is_sensitive': False})
        print(f"Return Type: {type(env_filter)}")
        print(f"List Length: {len(env_filter)}")
        print(f"First Item Type: {type(env_filter[0]) if env_filter else 'None'}")
        if env_filter:
            print(f"First Item: {env_filter[0]}")
        
        print("\n7. ENVIRONMENT UPDATE ÇIKTISI:")
        print("-" * 30)
        update_data = {'description': 'Updated description for testing'}
        updated_env = orchestration.environment_update(session, env_id, **update_data)
        print(f"Return Type: {type(updated_env)}")
        print(f"Return Value: {updated_env}")
        
        print("\n8. ENVIRONMENT DELETE ÇIKTISI:")
        print("-" * 30)
        deleted_env = orchestration.environment_delete(session, env_id)
        print(f"Return Type: {type(deleted_env)}")
        print(f"Return Value: {deleted_env}")

if __name__ == "__main__":
    test_environment_outputs()
