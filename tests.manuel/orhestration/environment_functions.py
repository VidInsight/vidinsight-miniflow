"""
Manual tests for DatabaseOrchestration environment functions
Run these tests manually to verify environment variable operations
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from miniflow.database_manager.engine import DatabaseEngine
from miniflow.database_manager.config import get_sqlite_config
from miniflow.database_manager.orchestration import DatabaseOrchestration
from miniflow.database_manager.models import Base
from miniflow.exceptions import ValidationError, BusinessLogicError

def test_environment_creation():
    """Test environment variable creation"""
    print("=== Testing Environment Variable Creation ===")
    
    config = get_sqlite_config(db_name='test_environment.db')
    engine = DatabaseEngine(config)
    engine.create_tables(Base.metadata)  # Create tables if they don't exist
    orchestration = DatabaseOrchestration()
    
    with engine.get_session_context() as session:
        try:
            # Test 1: Basic environment variable
            env_data = {
                "name": "DATABASE_URL",
                "value": "postgresql://user:pass@localhost:5432/miniflow",
                "description": "Main database connection string",
                "is_sensitive": True
            }
            
            result = orchestration.environment_create(session, **env_data)
            print(f"✓ Environment variable created: {result.id}")
            print(f"  Name: {result.name}")
            print(f"  Is sensitive: {result.is_sensitive}")
            
            # Test 2: API configuration
            api_config = {
                "key": "API_BASE_URL",
                "value": "https://api.miniflow.com/v1",
                "description": "Base URL for external API",
                "is_active": True,
                "is_secret": False,
                "category": "api",
                "metadata": {"version": "v1", "timeout": "30s"}
            }
            
            result2 = orchestration.environment_create(session, **api_config)
            print(f"✓ API config created: {result2.id}")
            print(f"  Key: {result2.key}")
            print(f"  Value: {result2.value}")
            
            # Test 3: Secret token
            secret_token = {
                "key": "JWT_SECRET_KEY",
                "value": "super_secret_jwt_key_12345",
                "description": "JWT token signing key",
                "is_active": True,
                "is_secret": True,
                "category": "security",
                "metadata": {"algorithm": "HS256", "expires": "never"}
            }
            
            result3 = orchestration.environment_create(session, **secret_token)
            print(f"✓ Secret token created: {result3.id}")
            print(f"  Key: {result3.key}")
            print(f"  Is secret: {result3.is_secret}")
            
            # session.commit() - handled by context manager
            
        except Exception as e:
            print(f"✗ Error: {e}")
            # session.rollback() - handled by context manager

def test_environment_update():
    """Test environment variable update functionality"""
    print("\n=== Testing Environment Variable Update ===")
    
    config = get_sqlite_config(db_name='test_environment.db')
    engine = DatabaseEngine(config)
    engine.create_tables(Base.metadata)  # Create tables if they don't exist
    orchestration = DatabaseOrchestration()
    
    with engine.get_session_context() as session:
        try:
            # First create an environment variable to update
            original_data = {
                "key": "UPDATE_TEST_VAR",
                "value": "original_value",
                "description": "Variable for update testing",
                "is_active": True,
                "is_secret": False,
                "category": "testing",
                "metadata": {"version": "1.0", "stage": "development"}
            }
            
            created_env = orchestration.environment_create(session, **original_data)
            env_id = created_env.id
            print(f"✓ Created environment variable for update test: {env_id}")
            
            # Test update - change value and metadata
            update_data = {
                "value": "updated_value_with_new_content",
                "description": "Updated description with more details",
                "is_secret": True,  # Change to secret
                "category": "production",
                "metadata": {
                    "version": "2.0",
                    "stage": "production",
                    "last_updated": "2024-01-01",
                    "updated_by": "admin"
                }
            }
            
            updated_env = orchestration.environment_update(session, env_id, **update_data)
            print(f"✓ Updated environment variable: {updated_env.id}")
            print(f"  New value: {'[HIDDEN]' if updated_env.is_secret else updated_env.value}")
            print(f"  New category: {updated_env.category}")
            print(f"  Is secret: {updated_env.is_secret}")
            
            # Test partial update - only change is_active status
            partial_update = {
                "is_active": False,
                "metadata": {"status": "disabled", "reason": "temporarily_disabled"}
            }
            
            partial_updated = orchestration.environment_update(session, env_id, **partial_update)
            print(f"✓ Partially updated environment variable")
            print(f"  Is active: {partial_updated.is_active}")
            print(f"  Key unchanged: {partial_updated.key}")
            
            # session.commit() - handled by context manager
            
        except Exception as e:
            print(f"✗ Error: {e}")
            # session.rollback() - handled by context manager

def test_environment_get_and_list():
    """Test environment variable retrieval functions"""
    print("\n=== Testing Environment Variable Get and List ===")
    
    config = get_sqlite_config(db_name='test_environment.db')
    engine = DatabaseEngine(config)
    engine.create_tables(Base.metadata)  # Create tables if they don't exist
    orchestration = DatabaseOrchestration()
    
    with engine.get_session_context() as session:
        try:
            # Get all environment variables
            all_envs = orchestration.environment_list(session)
            print(f"✓ Retrieved {len(all_envs)} environment variables")
            
            if all_envs:
                # Test get by ID
                first_env_id = all_envs[0]['id']
                retrieved_env = orchestration.environment_get(session, first_env_id)
                print(f"✓ Retrieved specific environment variable: {retrieved_env['id']}")
                print(f"  Key: {retrieved_env['key']}")
                print(f"  Category: {retrieved_env['category']}")
                print(f"  Is active: {retrieved_env['is_active']}")
                
                # Test environment exists
                exists = orchestration.environment_exists(session, first_env_id)
                print(f"✓ Environment exists check: {exists}")
                
                # Test non-existent environment
                exists_invalid = orchestration.environment_exists(session, "INVALID-ID")
                print(f"✓ Invalid environment exists check: {exists_invalid}")
            
            # Test count
            env_count = orchestration.environment_count(session)
            print(f"✓ Total environment variable count: {env_count}")
            
        except Exception as e:
            print(f"✗ Error: {e}")

def test_environment_filter():
    """Test environment variable filtering"""
    print("\n=== Testing Environment Variable Filter ===")
    
    config = get_sqlite_config(db_name='test_environment.db')
    engine = DatabaseEngine(config)
    engine.create_tables(Base.metadata)  # Create tables if they don't exist
    orchestration = DatabaseOrchestration()
    
    with engine.get_session_context() as session:
        try:
            # Create environment variables with different properties for filtering
            test_envs = [
                {
                    "key": "PRODUCTION_DB_HOST",
                    "value": "prod-db.company.com",
                    "description": "Production database host",
                    "is_active": True,
                    "is_secret": False,
                    "category": "database"
                },
                {
                    "key": "PRODUCTION_DB_PASSWORD",
                    "value": "super_secret_password",
                    "description": "Production database password",
                    "is_active": True,
                    "is_secret": True,
                    "category": "database"
                },
                {
                    "key": "API_RATE_LIMIT",
                    "value": "1000",
                    "description": "API rate limit per hour",
                    "is_active": True,
                    "is_secret": False,
                    "category": "api"
                },
                {
                    "key": "LEGACY_SERVICE_URL",
                    "value": "http://legacy.internal.com",
                    "description": "Legacy service endpoint",
                    "is_active": False,
                    "is_secret": False,
                    "category": "legacy"
                }
            ]
            
            created_ids = []
            for env_data in test_envs:
                result = orchestration.environment_create(session, **env_data)
                created_ids.append(result.id)
                print(f"✓ Created test environment variable: {result.key}")
            
            # Test filter by category
            db_filter = {'category': 'database'}
            db_envs = orchestration.environment_filter(session, db_filter)
            print(f"✓ Found {len(db_envs)} database environment variables")
            
            # Test filter by is_secret
            secret_filter = {'is_secret': True}
            secret_envs = orchestration.environment_filter(session, secret_filter)
            print(f"✓ Found {len(secret_envs)} secret environment variables")
            
            # Test filter by is_active
            active_filter = {'is_active': True}
            active_envs = orchestration.environment_filter(session, active_filter)
            print(f"✓ Found {len(active_envs)} active environment variables")
            
            # Test filter by key pattern (contains 'PRODUCTION')
            prod_filter = {'key': '%PRODUCTION%'}
            prod_envs = orchestration.environment_filter(session, prod_filter)
            print(f"✓ Found {len(prod_envs)} production environment variables")
            
            # session.commit() - handled by context manager
            
        except Exception as e:
            print(f"✗ Error: {e}")
            # session.rollback() - handled by context manager

def test_environment_delete():
    """Test environment variable deletion"""
    print("\n=== Testing Environment Variable Delete ===")
    
    config = get_sqlite_config(db_name='test_environment.db')
    engine = DatabaseEngine(config)
    engine.create_tables(Base.metadata)  # Create tables if they don't exist
    orchestration = DatabaseOrchestration()
    
    with engine.get_session_context() as session:
        try:
            # Create an environment variable to delete
            delete_env_data = {
                "key": "TEMP_DELETE_ME",
                "value": "temporary_value",
                "description": "This environment variable will be deleted",
                "is_active": False,
                "is_secret": False,
                "category": "temporary",
                "metadata": {"purpose": "deletion_test"}
            }
            
            created_env = orchestration.environment_create(session, **delete_env_data)
            env_id = created_env.id
            print(f"✓ Created environment variable to delete: {env_id}")
            
            # Verify it exists
            exists_before = orchestration.environment_exists(session, env_id)
            print(f"✓ Environment variable exists before deletion: {exists_before}")
            
            # Delete the environment variable
            deleted_env = orchestration.environment_delete(session, env_id)
            print(f"✓ Deleted environment variable: {deleted_env.id}")
            print(f"  Deleted key: {deleted_env.key}")
            
            # Verify it's gone
            exists_after = orchestration.environment_exists(session, env_id)
            print(f"✓ Environment variable exists after deletion: {exists_after}")
            
            # Test deleting non-existent environment variable
            try:
                orchestration.environment_delete(session, "INVALID-ENV-ID")
                print("✗ Should have failed for invalid ID")
            except Exception as e:
                print(f"✓ Correctly failed for invalid ID: {type(e).__name__}")
                
            # session.commit() - handled by context manager
            
        except Exception as e:
            print(f"✗ Error: {e}")
            # session.rollback() - handled by context manager

def test_environment_delete_all():
    """Test deleting all environment variables"""
    print("\n=== Testing Environment Variable Delete All ===")
    
    config = get_sqlite_config(db_name='test_environment.db')
    engine = DatabaseEngine(config)
    engine.create_tables(Base.metadata)  # Create tables if they don't exist
    orchestration = DatabaseOrchestration()
    
    with engine.get_session_context() as session:
        try:
            # Create some test environment variables
            test_envs = [
                {
                    "key": "BULK_DELETE_1",
                    "value": "value1",
                    "description": "First test variable for bulk delete",
                    "is_active": True,
                    "is_secret": False,
                    "category": "test"
                },
                {
                    "key": "BULK_DELETE_2", 
                    "value": "value2",
                    "description": "Second test variable for bulk delete",
                    "is_active": True,
                    "is_secret": False,
                    "category": "test"
                },
                {
                    "key": "BULK_DELETE_3",
                    "value": "value3", 
                    "description": "Third test variable for bulk delete",
                    "is_active": True,
                    "is_secret": False,
                    "category": "test"
                }
            ]
            
            for env_data in test_envs:
                result = orchestration.environment_create(session, **env_data)
                print(f"✓ Created test env for bulk delete: {result.key}")
            
            # Count before deletion
            count_before = orchestration.environment_count(session)
            print(f"✓ Environment variables before bulk delete: {count_before}")
            
            # Delete all environment variables
            deleted_count = orchestration.environment_delete_all(session)
            print(f"✓ Bulk deleted {deleted_count} environment variables")
            
            # Count after deletion
            count_after = orchestration.environment_count(session)
            print(f"✓ Environment variables after bulk delete: {count_after}")
            
            # session.commit() - handled by context manager
            
        except Exception as e:
            print(f"✗ Error: {e}")
            # session.rollback() - handled by context manager

def test_environment_security_features():
    """Test environment variable security features"""
    print("\n=== Testing Environment Variable Security Features ===")
    
    config = get_sqlite_config(db_name='test_environment.db')
    engine = DatabaseEngine(config)
    engine.create_tables(Base.metadata)  # Create tables if they don't exist
    orchestration = DatabaseOrchestration()
    
    with engine.get_session_context() as session:
        try:
            # Create secret environment variables
            secret_envs = [
                {
                    "key": "DATABASE_PASSWORD",
                    "value": "super_secret_db_password_123",
                    "description": "Database password - should be hidden",
                    "is_active": True,
                    "is_secret": True,
                    "category": "security",
                    "metadata": {"encryption": "AES256", "last_rotated": "2024-01-01"}
                },
                {
                    "key": "API_TOKEN",
                    "value": "sk-1234567890abcdef",
                    "description": "API token for external service",
                    "is_active": True,
                    "is_secret": True,
                    "category": "security",
                    "metadata": {"scope": "read_write", "expires": "2024-12-31"}
                },
                {
                    "key": "PUBLIC_API_URL",
                    "value": "https://api.example.com",
                    "description": "Public API URL - not secret",
                    "is_active": True,
                    "is_secret": False,
                    "category": "configuration",
                    "metadata": {"version": "v1", "status": "stable"}
                }
            ]
            
            created_secrets = []
            for env_data in secret_envs:
                result = orchestration.environment_create(session, **env_data)
                created_secrets.append(result)
                secret_status = "SECRET" if result.is_secret else "PUBLIC"
                print(f"✓ Created {secret_status} env: {result.key}")
            
            # Test retrieval of secret values
            for env in created_secrets:
                retrieved = orchestration.environment_get(session, env.id)
                if retrieved['is_secret']:
                    print(f"  Secret {retrieved['key']}: Value hidden in logs")
                else:
                    print(f"  Public {retrieved['key']}: {retrieved['value']}")
            
            # Test filtering secret vs non-secret
            secret_filter = {'is_secret': True}
            secret_envs_list = orchestration.environment_filter(session, secret_filter)
            print(f"✓ Found {len(secret_envs_list)} secret environment variables")
            
            public_filter = {'is_secret': False}
            public_envs_list = orchestration.environment_filter(session, public_filter)
            print(f"✓ Found {len(public_envs_list)} public environment variables")
            
            # session.commit() - handled by context manager
            
        except Exception as e:
            print(f"✗ Error: {e}")
            # session.rollback() - handled by context manager

def run_all_environment_tests():
    """Run all environment variable tests"""
    print("Starting Environment Variable Function Tests")
    print("=" * 50)
    
    test_environment_creation()
    test_environment_update()
    test_environment_get_and_list()
    test_environment_filter()
    test_environment_delete()
    test_environment_delete_all()
    test_environment_security_features()
    
    print("\n" + "=" * 50)
    print("Environment variable tests completed!")

if __name__ == "__main__":
    run_all_environment_tests()
