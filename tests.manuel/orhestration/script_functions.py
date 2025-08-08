"""
Manual tests for DatabaseOrchestration script functions
Run these tests manually to verify script operations
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from miniflow.database_manager.engine import DatabaseEngine
from miniflow.database_manager.config import get_sqlite_config
from miniflow.database_manager.orchestration import DatabaseOrchestration
from miniflow.database_manager.models import Base, ScriptType
from miniflow.exceptions import ValidationError, BusinessLogicError

def test_script_creation():
    """Test script creation"""
    print("=== Testing Script Creation ===")
    
    config = get_sqlite_config(db_name='test_script.db')
    engine = DatabaseEngine(config)
    engine.create_tables(Base.metadata)  # Create tables if they don't exist
    orchestration = DatabaseOrchestration()
    
    with engine.get_session_context() as session:
        try:
            # Test 1: Basic script creation
            script_data = {
                "name": "Test Script",
                "description": "A test script for manual testing",
                "language": ScriptType.PYTHON,
                "script_path": "/path/to/test_script.py"
            }
            
            result = orchestration.script_create(session, **script_data)
            print(f"✓ Script created: {result.id}")
            print(f"  Name: {result.name}")
            print(f"  Language: {result.language}")
            print(f"  Path: {result.script_path}")
            
            # Test 2: Another script with different type
            batch_script_data = {
                "name": "Batch Script",
                "description": "Batch processing script", 
                "language": ScriptType.BASH,
                "script_path": "/scripts/batch_process.sh"
            }
            
            result2 = orchestration.script_create(session, **batch_script_data)
            print(f"✓ Second script created: {result2.id}")
            print(f"  Name: {result2.name}")
            print(f"  Type: {result2.script_type}")
            
            # session.commit() - handled by context manager
            
        except Exception as e:
            print(f"✗ Error: {e}")
            # session.rollback() - handled by context manager

def test_script_update():
    """Test script update functionality"""
    print("\n=== Testing Script Update ===")
    
    config = get_sqlite_config(db_name='test_script.db')
    engine = DatabaseEngine(config)
    engine.create_tables(Base.metadata)  # Create tables if they don't exist
    orchestration = DatabaseOrchestration()
    
    with engine.get_session_context() as session:
        try:
            # First create a script to update
            original_data = {
                "name": "Original Script",
                "description": "Original description",
                "language": "python",
                "script_path": "/original/path.py",
                "is_active": True,
                "version": "1.0.0",
                "tags": ["original"],
                "metadata": {"status": "draft"}
            }
            
            created_script = orchestration.script_create(session, **original_data)
            script_id = created_script.id
            print(f"✓ Created script for update test: {script_id}")
            
            # Test update - change multiple fields
            update_data = {
                "name": "Updated Script Name",
                "description": "Updated description with more details",
                "script_path": "/updated/path.py",
                "version": "2.0.0", 
                "tags": ["updated", "production"],
                "metadata": {"status": "production", "last_modified": "2024-01-01"}
            }
            
            updated_script = orchestration.script_update(session, script_id, **update_data)
            print(f"✓ Updated script: {updated_script.id}")
            print(f"  New name: {updated_script.name}")
            print(f"  New version: {updated_script.version}")
            print(f"  New path: {updated_script.script_path}")
            
            # Test partial update - only change description
            partial_update = {
                "description": "Partially updated description only"
            }
            
            partial_updated = orchestration.script_update(session, script_id, **partial_update)
            print(f"✓ Partially updated script description")
            print(f"  Description: {partial_updated.description}")
            print(f"  Name unchanged: {partial_updated.name}")
            
            # session.commit() - handled by context manager
            
        except Exception as e:
            print(f"✗ Error: {e}")
            # session.rollback() - handled by context manager

def test_script_get_and_list():
    """Test script retrieval functions"""
    print("\n=== Testing Script Get and List ===")
    
    config = get_sqlite_config(db_name='test_script.db')
    engine = DatabaseEngine(config)
    engine.create_tables(Base.metadata)  # Create tables if they don't exist
    orchestration = DatabaseOrchestration()
    
    with engine.get_session_context() as session:
        try:
            # Get all scripts first
            all_scripts = orchestration.script_list(session)
            print(f"✓ Retrieved {len(all_scripts)} scripts")
            
            if all_scripts:
                # Test get by ID
                first_script_id = all_scripts[0].id
                retrieved_script = orchestration.script_get(session, first_script_id)
                print(f"✓ Retrieved specific script: {retrieved_script.id}")
                print(f"  Name: {retrieved_script.name}")
                print(f"  Type: {retrieved_script.script_type}")
                print(f"  Active: {retrieved_script.is_active}")
                
                # Test script exists
                exists = orchestration.script_exists(session, first_script_id)
                print(f"✓ Script exists check: {exists}")
                
                # Test non-existent script
                exists_invalid = orchestration.script_exists(session, "INVALID-ID")
                print(f"✓ Invalid script exists check: {exists_invalid}")
            
            # Test count
            script_count = orchestration.script_count(session)
            print(f"✓ Total script count: {script_count}")
            
        except Exception as e:
            print(f"✗ Error: {e}")

def test_script_filter():
    """Test script filtering"""
    print("\n=== Testing Script Filter ===")
    
    config = get_sqlite_config(db_name='test_script.db')
    engine = DatabaseEngine(config)
    engine.create_tables(Base.metadata)  # Create tables if they don't exist
    orchestration = DatabaseOrchestration()
    
    with engine.get_session_context() as session:
        try:
            # Create scripts with different properties for filtering
            test_scripts = [
                {
                    "name": "Python Analytics Script",
                    "description": "Analytics processing",
                    "language": "python",
                    "script_path": "/analytics/process.py",
                    "is_active": True,
                    "version": "1.0.0",
                    "tags": ["analytics", "python"]
                },
                {
                    "name": "Data Cleanup Script", 
                    "description": "Data cleanup batch job",
                    "language": "bash",
                    "script_path": "/cleanup/data_cleanup.sh",
                    "is_active": False,
                    "version": "0.9.0",
                    "tags": ["cleanup", "batch"]
                },
                {
                    "name": "Python ML Model",
                    "description": "Machine learning model training",
                    "language": "python", 
                    "script_path": "/ml/train_model.py",
                    "is_active": True,
                    "version": "3.1.0",
                    "tags": ["ml", "python"]
                }
            ]
            
            created_ids = []
            for script_data in test_scripts:
                result = orchestration.script_create(session, **script_data)
                created_ids.append(result.id)
                print(f"✓ Created test script: {result.name}")
            
            # Test filter by script_type
            python_filter = {'language': 'python'}
            python_scripts = orchestration.script_filter(session, python_filter)
            print(f"✓ Found {len(python_scripts)} Python scripts")
            
            # Test filter by is_active
            active_filter = {'is_active': True}
            active_scripts = orchestration.script_filter(session, active_filter)
            print(f"✓ Found {len(active_scripts)} active scripts")
            
            # Test filter by name pattern
            name_filter = {'name': 'Python%'}  # Scripts starting with 'Python'
            name_scripts = orchestration.script_filter(session, name_filter)
            print(f"✓ Found {len(name_scripts)} scripts starting with 'Python'")
            
            # session.commit() - handled by context manager
            
        except Exception as e:
            print(f"✗ Error: {e}")
            # session.rollback() - handled by context manager

def test_script_delete():
    """Test script deletion"""
    print("\n=== Testing Script Delete ===")
    
    config = get_sqlite_config(db_name='test_script.db')
    engine = DatabaseEngine(config)
    engine.create_tables(Base.metadata)  # Create tables if they don't exist
    orchestration = DatabaseOrchestration()
    
    with engine.get_session_context() as session:
        try:
            # Create a script to delete
            delete_script_data = {
                "name": "Script to Delete",
                "description": "This script will be deleted",
                "language": "python",
                "script_path": "/temp/delete_me.py",
                "is_active": False,
                "version": "0.1.0",
                "tags": ["temporary", "delete"],
                "metadata": {"purpose": "deletion_test"}
            }
            
            created_script = orchestration.script_create(session, **delete_script_data)
            script_id = created_script.id
            print(f"✓ Created script to delete: {script_id}")
            
            # Verify it exists
            exists_before = orchestration.script_exists(session, script_id)
            print(f"✓ Script exists before deletion: {exists_before}")
            
            # Delete the script
            deleted_script = orchestration.script_delete(session, script_id)
            print(f"✓ Deleted script: {deleted_script.id}")
            print(f"  Deleted name: {deleted_script.name}")
            
            # Verify it's gone
            exists_after = orchestration.script_exists(session, script_id)
            print(f"✓ Script exists after deletion: {exists_after}")
            
            # Test deleting non-existent script
            try:
                orchestration.script_delete(session, "INVALID-SCRIPT-ID")
                print("✗ Should have failed for invalid ID")
            except Exception as e:
                print(f"✓ Correctly failed for invalid ID: {type(e).__name__}")
                
            # session.commit() - handled by context manager
            
        except Exception as e:
            print(f"✗ Error: {e}")
            # session.rollback() - handled by context manager

def test_script_advanced_operations():
    """Test advanced script operations"""
    print("\n=== Testing Advanced Script Operations ===")
    
    config = get_sqlite_config(db_name='test_script.db')
    engine = DatabaseEngine(config)
    engine.create_tables(Base.metadata)  # Create tables if they don't exist
    orchestration = DatabaseOrchestration()
    
    with engine.get_session_context() as session:
        try:
            # Create scripts with complex metadata and tags
            advanced_script = {
                "name": "Advanced Analytics Pipeline",
                "description": "Complex analytics pipeline with multiple stages",
                "language": "python",
                "script_path": "/pipelines/advanced_analytics.py",
                "is_active": True,
                "version": "4.2.1",
                "tags": ["analytics", "pipeline", "production", "high-priority"],
                "metadata": {
                    "author": "data_team",
                    "last_modified": "2024-01-15",
                    "dependencies": ["pandas", "numpy", "scikit-learn"],
                    "estimated_runtime": "30min",
                    "resource_requirements": {
                        "cpu": "4 cores",
                        "memory": "8GB",
                        "disk": "100GB"
                    },
                    "schedule": {
                        "frequency": "daily",
                        "time": "02:00"
                    }
                }
            }
            
            created = orchestration.script_create(session, **advanced_script)
            print(f"✓ Created advanced script: {created.id}")
            print(f"  Tags: {created.tags}")
            print(f"  Metadata keys: {list(created.metadata.keys()) if created.metadata else 'None'}")
            
            # Test updating complex metadata
            metadata_update = {
                "metadata": {
                    "author": "updated_data_team",
                    "last_modified": "2024-01-20",
                    "dependencies": ["pandas", "numpy", "scikit-learn", "tensorflow"],
                    "estimated_runtime": "25min",
                    "resource_requirements": {
                        "cpu": "6 cores",
                        "memory": "12GB", 
                        "disk": "150GB"
                    },
                    "performance_metrics": {
                        "avg_execution_time": "23min",
                        "success_rate": "99.5%"
                    }
                }
            }
            
            updated = orchestration.script_update(session, created.id, **metadata_update)
            print(f"✓ Updated script metadata")
            print(f"  New metadata keys: {list(updated.metadata.keys()) if updated.metadata else 'None'}")
            
            # session.commit() - handled by context manager
            
        except Exception as e:
            print(f"✗ Error: {e}")
            # session.rollback() - handled by context manager

def run_all_script_tests():
    """Run all script tests"""
    print("Starting Script Function Tests")
    print("=" * 50)
    
    test_script_creation()
    test_script_update()
    test_script_get_and_list()
    test_script_filter()
    test_script_delete()
    test_script_advanced_operations()
    
    print("\n" + "=" * 50)
    print("Script tests completed!")

if __name__ == "__main__":
    run_all_script_tests()
