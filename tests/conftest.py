import os
import pytest
import shutil
import tempfile
import atexit
from pathlib import Path
from typing import Dict, Any

# Global cleanup function for persistent database files
def cleanup_database_files():
    """Clean up any stray database files created during testing"""
    try:
        if os.path.exists(":memory:.db"):
            os.unlink(":memory:.db")
            print("Cleaned up :memory:.db file")
    except Exception as e:
        print(f"Failed to clean up :memory:.db: {e}")

# Register cleanup function to run when Python exits
atexit.register(cleanup_database_files)

# Pytest fixture for session-level cleanup
@pytest.fixture(scope="session", autouse=True)
def cleanup_after_tests():
    """Automatically clean up database files after test session"""
    yield  # Tests run here
    cleanup_database_files()

# Miniflow Database Manager Imports
from miniflow.database_manager import DatabaseConfig, get_sqlite_config
from miniflow.database_manager import Base, create_database_engine
from miniflow.database_manager import DatabaseOrchestration
from miniflow.database_manager.config import DatabaseType, EngineConfig, get_database_config
from miniflow.database_manager.config import get_sqlite_config, get_postgresql_config, get_mysql_config


# ======================================================================================= FIXTURE :: DATABASE MANAGER ==
# ======================================================================================= FIXTURE :: CONFIG TESTING ==

@pytest.fixture
def default_engine_config():
    """Default EngineConfig fixture"""
    return EngineConfig()

@pytest.fixture
def custom_engine_config():
    """Custom EngineConfig fixture with non-default values"""
    return EngineConfig(
        pool_size=5,
        max_overflow=10,
        pool_timeout=60,
        pool_recycle=1800,
        pool_pre_ping=False,
        echo=True,
        echo_pool=True,
        autocommit=True,
        autoflush=False,
        expire_on_commit=False,
        isolation_level="READ_COMMITTED",
        connect_args={"charset": "utf8mb4", "timeout": 30}
    )

@pytest.fixture
def minimal_engine_config():
    """Minimal EngineConfig fixture with only required parameters"""
    return EngineConfig(
        pool_size=1,
        echo=True,
        isolation_level="SERIALIZABLE"
    )

@pytest.fixture
def sqlite_database_config():
    """SQLite DatabaseConfig fixture"""
    return DatabaseConfig(
        db_name="test_db",
        db_type=DatabaseType.SQLITE,
        engine_config=EngineConfig(pool_size=1)
    )

@pytest.fixture
def mysql_database_config():
    """MySQL DatabaseConfig fixture"""
    return DatabaseConfig(
        db_name="test_db",
        db_type=DatabaseType.MYSQL,
        host="localhost",
        port=3306,
        username="root",
        password="password123",
        engine_config=EngineConfig(pool_size=15)
    )

@pytest.fixture
def postgresql_database_config():
    """PostgreSQL DatabaseConfig fixture"""
    return DatabaseConfig(
        db_name="test_db",
        db_type=DatabaseType.POSTGRESQL,
        host="pg.example.com",
        port=5432,
        username="postgres",
        password="secret",
        engine_config=EngineConfig(pool_size=20)
    )

@pytest.fixture
def empty_database_config():
    """Empty DatabaseConfig fixture with default values"""
    return DatabaseConfig()

@pytest.fixture
def database_config_without_password():
    """DatabaseConfig fixture without password"""
    return DatabaseConfig(
        db_name="test_db",
        db_type=DatabaseType.MYSQL,
        host="localhost",
        port=3306,
        username="user"
    )

@pytest.fixture
def sample_connection_strings():
    """Sample connection strings for different database types"""
    return {
        "sqlite": "sqlite:///test_db.db",
        "mysql": "mysql+pymysql://root:password123@localhost:3306/test_db",
        "postgresql": "postgresql+psycopg2://postgres:secret@pg.example.com:5432/test_db"
    }

@pytest.fixture
def sample_engine_configs():
    """Sample EngineConfig objects with different configurations"""
    return {
        "default": EngineConfig(),
        "custom": EngineConfig(
            pool_size=5,
            max_overflow=10,
            echo=True,
            isolation_level="READ_COMMITTED",
            connect_args={"charset": "utf8mb4", "timeout": 30}
        ),
        "minimal": EngineConfig(
            pool_size=1,
            echo=True,
            isolation_level="SERIALIZABLE"
        ),
        "with_connect_args": EngineConfig(
            pool_size=15,
            echo=True,
            connect_args={"key": "value"},
            isolation_level="SERIALIZABLE"
        )
    }

@pytest.fixture
def sample_database_configs():
    """Sample DatabaseConfig objects for different database types"""
    return {
        "sqlite": DatabaseConfig(
            db_name="test_db",
            db_type=DatabaseType.SQLITE
        ),
        "mysql": DatabaseConfig(
            db_name="test_db",
            db_type=DatabaseType.MYSQL,
            host="localhost",
            port=3306,
            username="root",
            password="password123"
        ),
        "postgresql": DatabaseConfig(
            db_name="test_db",
            db_type=DatabaseType.POSTGRESQL,
            host="pg.example.com",
            port=5432,
            username="postgres",
            password="secret"
        ),
        "mysql_without_password": DatabaseConfig(
            db_name="test_db",
            db_type=DatabaseType.MYSQL,
            host="localhost",
            port=3306,
            username="user"
        )
    }

@pytest.fixture
def factory_function_configs():
    """Configs created by factory functions for testing"""
    return {
        "sqlite_default": get_sqlite_config(),
        "sqlite_custom": get_sqlite_config(db_name="custom.db"),
        "postgresql_default": get_postgresql_config(),
        "postgresql_custom": get_postgresql_config(
            db_name="custom_db",
            host="pg.example.com",
            port=5433,
            username="custom_user",
            password="custom_pass"
        ),
        "mysql_default": get_mysql_config(),
        "mysql_custom": get_mysql_config(
            db_name="app_db",
            host="mysql.example.com",
            port=3307,
            username="app_user",
            password="app_pass"
        )
    }

@pytest.fixture
def expected_engine_config_dict():
    """Expected dictionary representation of EngineConfig"""
    return {
        'pool_size': 15,
        'max_overflow': 20,
        'pool_timeout': 30,
        'pool_recycle': 3600,
        'pool_pre_ping': True,
        'connect_args': {"key": "value"},
        'echo': True,
        'echo_pool': False,
        'isolation_level': 'SERIALIZABLE',
    }

@pytest.fixture
def expected_database_config_dict_masked():
    """Expected dictionary representation of DatabaseConfig with masked password"""
    return {
        'db_name': 'test_db',
        'db_type': 'mysql',
        'host': 'localhost',
        'port': 3306,
        'username': 'user',
        'password': '***masked***',
        'engine_config': {
            'pool_size': 10,
            'max_overflow': 20,
            'pool_timeout': 30,
            'pool_recycle': 3600,
            'pool_pre_ping': True,
            'connect_args': {},
            'echo': False,
            'echo_pool': False,
            'isolation_level': None,
        }
    }

@pytest.fixture
def expected_database_config_dict_unmasked():
    """Expected dictionary representation of DatabaseConfig without masked password"""
    return {
        'db_name': 'test_db',
        'db_type': 'mysql',
        'host': 'localhost',
        'port': 3306,
        'username': 'user',
        'password': 'secret123',
        'engine_config': {
            'pool_size': 10,
            'max_overflow': 20,
            'pool_timeout': 30,
            'pool_recycle': 3600,
            'pool_pre_ping': True,
            'connect_args': {},
            'echo': False,
            'echo_pool': False,
            'isolation_level': None,
        }
    }

# ======================================================================================= FIXTURE :: MODELS TESTING ==

@pytest.fixture
def test_database_session():
    """True in-memory SQLite database session for testing"""
    import uuid
    import tempfile
    import os
    from miniflow.database_manager import create_database_engine
    from sqlalchemy.orm import sessionmaker
    
    # Use true in-memory database for maximum speed
    # Cleanup system handles any stray ":memory:.db" files
    config = get_sqlite_config(db_name=":memory:")
    
    try:
        
        db_engine = create_database_engine(config)
        db_engine.start()  # Start the engine
        
        # Get the actual SQLAlchemy engine
        sqlalchemy_engine = db_engine.get_engine
        
        # Create all tables
        from miniflow.database_manager.models import Base
        Base.metadata.create_all(sqlalchemy_engine)
        
        # Create session
        Session = sessionmaker(bind=sqlalchemy_engine)
        session = Session()
        
        yield session
        
    finally:
        # Comprehensive cleanup
        try:
            # Rollback any uncommitted transactions
            session.rollback()
        except:
            pass
            
        try:
            # Close session
            session.close()
        except:
            pass
            
        try:
            # Drop all tables to ensure clean state
            Base.metadata.drop_all(sqlalchemy_engine)
        except:
            pass
            
        try:
            # Dispose of engine connection pool
            sqlalchemy_engine.dispose()
        except:
            pass
            
        try:
            # Stop our database engine
            db_engine.stop()
        except:
            pass
            
        # Clean up any stray :memory:.db files (system-level SQLAlchemy issue)
        try:
            if os.path.exists(":memory:.db"):
                os.unlink(":memory:.db")
                print("Cleaned up stray :memory:.db file")
        except:
            pass

@pytest.fixture
def sample_workflow_data():
    """Sample workflow data for testing"""
    return {
        "name": "Test Workflow",
        "description": "Test workflow description",
        "status": "active",
        "priority": 1
    }

@pytest.fixture
def sample_node_data():
    """Sample node data for testing"""
    return {
        "name": "Test Node",
        "params": {"param1": "value1", "param2": "value2"},
        "max_retries": 3,
        "timeout_seconds": 300
    }

@pytest.fixture
def sample_script_data():
    """Sample script data for testing"""
    return {
        "name": "Test Script",
        "description": "Test script description",
        "language": "python",
        "script_path": "/path/to/script.py",
        "input_params": {"input1": "string", "input2": "int"},
        "output_params": {"output1": "string", "output2": "bool"},
        "test_status": "untested"
    }

@pytest.fixture
def sample_execution_data():
    """Sample execution data for testing"""
    return {
        "status": "pending",
        "pending_nodes": 5,
        "executed_nodes": 0,
        "results": {"step1": "completed", "step2": "pending"}
    }

@pytest.fixture
def sample_edge_data():
    """Sample edge data for testing"""
    return {
        "condition_type": "success"
    }

@pytest.fixture
def sample_audit_log_data():
    """Sample audit log data for testing"""
    return {
        "table_name": "workflows",
        "record_id": "WF1234567890",
        "action": "CREATE",
        "old_values": None,
        "new_values": {"name": "New Workflow", "status": "draft"}
    }

@pytest.fixture
def workflow_with_nodes(test_database_session):
    """Create a workflow with nodes for testing relationships"""
    import uuid
    from miniflow.database_manager.models import Workflow, Node, Script
    
    # Generate unique names for this test
    unique_id = uuid.uuid4().hex[:8]
    
    # Create script
    script = Script(
        name=f"Test Script {unique_id}",
        language="python",
        script_path="/test/script.py"
    )
    test_database_session.add(script)
    test_database_session.flush()
    
    # Create workflow
    workflow = Workflow(
        name=f"Test Workflow {unique_id}",
        description="Test description",
        status="active"
    )
    test_database_session.add(workflow)
    test_database_session.flush()
    
    # Create nodes
    node1 = Node(
        workflow_id=workflow.id,
        script_id=script.id,
        name="Node 1",
        params={"param": "value"}
    )
    node2 = Node(
        workflow_id=workflow.id,
        script_id=script.id,
        name="Node 2",
        params={"param": "value"}
    )
    
    test_database_session.add_all([node1, node2])
    test_database_session.commit()
    
    return {
        "workflow": workflow,
        "nodes": [node1, node2],
        "script": script
    }

@pytest.fixture
def enum_test_data():
    """Test data for enum validations"""
    return {
        "workflow_statuses": ["active", "inactive", "draft", "archived"],
        "execution_statuses": ["pending", "running", "completed", "failed", "cancelled"],
        "execution_output_statuses": ["success", "failure", "timeout", "cancelled"],
        "condition_types": ["success", "failure", "always", "conditional"],
        "script_types": ["python"],
        "test_statuses": ["untested", "passed", "failed", "running"],
        "audit_actions": ["CREATE", "UPDATE", "DELETE", "EXECUTE", "ARCHIVE"],
        "archive_reasons": ["auto_cleanup", "manual_archive", "retention_policy", "system_cleanup"]
    }

# ======================================================================================= FIXTURE :: ENGINE TESTING ==

@pytest.fixture
def engine_sqlite_config():
    """SQLite DatabaseConfig for engine testing"""
    return get_sqlite_config(db_name=":memory:")

@pytest.fixture
def engine_invalid_config():
    """Invalid DatabaseConfig for error testing"""
    from miniflow.database_manager.config import DatabaseConfig, DatabaseType
    return DatabaseConfig(
        db_name="nonexistent_database",
        db_type=DatabaseType.SQLITE,
        host="invalid_host",
        port=99999
    )

@pytest.fixture
def mock_metadata():
    """Mock SQLAlchemy metadata for table operations testing"""
    from sqlalchemy import MetaData, Table, Column, Integer, String
    
    metadata = MetaData()
    
    # Create a simple test table
    test_table = Table(
        'test_table',
        metadata,
        Column('id', Integer, primary_key=True),
        Column('name', String(50))
    )
    
    return metadata

@pytest.fixture
def sample_sql_queries():
    """Sample SQL queries for testing"""
    return {
        "simple_select": "SELECT 1",
        "parameterized": "SELECT :value as result",
        "invalid": "INVALID SQL QUERY",
        "create_temp_table": "CREATE TEMPORARY TABLE temp_test (id INTEGER, name TEXT)",
        "insert_data": "INSERT INTO temp_test VALUES (1, 'test')",
        "select_data": "SELECT * FROM temp_test"
    }

@pytest.fixture
def db_engine_instance(engine_sqlite_config):
    """DatabaseEngine instance for testing (not started)"""
    from miniflow.database_manager.engine import DatabaseEngine
    return DatabaseEngine(engine_sqlite_config)

@pytest.fixture
def started_db_engine(engine_sqlite_config):
    """Started DatabaseEngine instance for testing"""
    from miniflow.database_manager.engine import DatabaseEngine
    
    engine = DatabaseEngine(engine_sqlite_config)
    engine.start()
    
    yield engine
    
    # Cleanup
    try:
        engine.stop()
    except:
        pass
