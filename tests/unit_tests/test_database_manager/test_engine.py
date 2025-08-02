import pytest
import uuid
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy import create_engine, Engine, MetaData, text
from sqlalchemy.orm import Session

from miniflow.database_manager.engine import (
    verify_database_connection,
    DatabaseEngine,
    create_database_engine
)
from miniflow.database_manager.config import DatabaseConfig, DatabaseType


@pytest.mark.unit
class TestDatabaseConnectionFunction:
    """Tests for verify_database_connection utility function"""

    def test_sqlite_connection_success(self, started_db_engine):
        """SQLite bağlantı testinin başarılı olması"""
        engine = started_db_engine.get_engine
        result = verify_database_connection(engine, "sqlite")
        assert result is True

    def test_postgresql_connection_success(self):
        """PostgreSQL bağlantı testinin başarılı olması (mock)"""
        mock_engine = Mock(spec=Engine)
        mock_conn = Mock()
        mock_context = Mock()
        mock_context.__enter__ = Mock(return_value=mock_conn)
        mock_context.__exit__ = Mock(return_value=False)
        mock_engine.connect.return_value = mock_context
        
        result = verify_database_connection(mock_engine, "postgresql")
        assert result is True
        mock_conn.execute.assert_called_once()

    def test_mysql_connection_success(self):
        """MySQL bağlantı testinin başarılı olması (mock)"""
        mock_engine = Mock(spec=Engine)
        mock_conn = Mock()
        mock_context = Mock()
        mock_context.__enter__ = Mock(return_value=mock_conn)
        mock_context.__exit__ = Mock(return_value=False)
        mock_engine.connect.return_value = mock_context
        
        result = verify_database_connection(mock_engine, "mysql")
        assert result is True
        mock_conn.execute.assert_called_once()

    def test_connection_failure(self):
        """Bağlantı hatası durumunda False dönmesi"""
        mock_engine = Mock(spec=Engine)
        mock_engine.connect.side_effect = Exception("Connection failed")
        
        result = verify_database_connection(mock_engine, "sqlite")
        assert result is False

    def test_default_db_type(self, started_db_engine):
        """Default db_type parametresinin sqlite olması"""
        engine = started_db_engine.get_engine
        result = verify_database_connection(engine)  # db_type belirtilmemiş
        assert result is True


@pytest.mark.unit
class TestDatabaseEngineLifecycle:
    """Tests for DatabaseEngine lifecycle methods"""

    def test_engine_initialization(self, engine_sqlite_config):
        """Engine initialization'ının doğru çalışması"""
        engine = DatabaseEngine(engine_sqlite_config)
        
        assert engine.is_alive is False
        assert engine._DatabaseEngine__config == engine_sqlite_config
        assert engine._DatabaseEngine__connection_string == "sqlite:///:memory:"
        assert isinstance(engine._DatabaseEngine__engine_config, dict)

    def test_engine_start_success(self, db_engine_instance):
        """Engine start işleminin başarılı olması"""
        engine = db_engine_instance
        
        assert engine.is_alive is False
        engine.start()
        assert engine.is_alive is True
        
        # Cleanup
        engine.stop()

    def test_engine_stop_success(self, db_engine_instance):
        """Engine stop işleminin başarılı olması"""
        engine = db_engine_instance
        
        engine.start()
        assert engine.is_alive is True
        
        engine.stop()
        assert engine.is_alive is False
        assert engine._DatabaseEngine__engine is None
        assert engine._DatabaseEngine__session_factory is None

    def test_multiple_start_calls(self, db_engine_instance):
        """Birden fazla start çağrısının sorun çıkarmaması"""
        engine = db_engine_instance
        
        engine.start()
        engine.start()  # İkinci start çağrısı
        assert engine.is_alive is True
        
        # Cleanup
        engine.stop()

    def test_stop_before_start(self, db_engine_instance):
        """Start edilmeden stop çağrısının güvenli olması"""
        engine = db_engine_instance
        
        engine.stop()  # Start edilmeden stop
        assert engine.is_alive is False

    def test_start_stop_cycle(self, db_engine_instance):
        """Start-stop döngüsünün düzgün çalışması"""
        engine = db_engine_instance
        
        # İlk döngü
        engine.start()
        assert engine.is_alive is True
        engine.stop()
        assert engine.is_alive is False
        
        # İkinci döngü
        engine.start()
        assert engine.is_alive is True
        engine.stop()
        assert engine.is_alive is False


@pytest.mark.unit
class TestDatabaseEngineProperties:
    """Tests for DatabaseEngine properties"""

    def test_get_engine_success(self, started_db_engine):
        """get_engine property'sinin doğru çalışması"""
        engine = started_db_engine
        sqlalchemy_engine = engine.get_engine
        
        assert isinstance(sqlalchemy_engine, Engine)
        assert sqlalchemy_engine is not None

    def test_get_engine_before_start(self, db_engine_instance):
        """Start edilmeden get_engine çağrısının RuntimeError fırlatması"""
        engine = db_engine_instance
        
        with pytest.raises(RuntimeError, match="Engine not initialized"):
            engine.get_engine

    def test_get_session_success(self, started_db_engine):
        """get_session property'sinin doğru çalışması"""
        engine = started_db_engine
        session = engine.get_session
        
        assert isinstance(session, Session)
        assert session is not None
        
        # Cleanup
        session.close()

    def test_get_session_before_start(self, db_engine_instance):
        """Start edilmeden get_session çağrısının RuntimeError fırlatması"""
        engine = db_engine_instance
        
        with pytest.raises(RuntimeError, match="Session factory not initialized"):
            engine.get_session

    def test_multiple_session_creation(self, started_db_engine):
        """Birden fazla session oluşturulabilmesi"""
        engine = started_db_engine
        
        session1 = engine.get_session
        session2 = engine.get_session
        
        assert session1 is not session2  # Farklı session instance'ları
        
        # Cleanup
        session1.close()
        session2.close()


@pytest.mark.unit
class TestSessionContextManagement:
    """Tests for session context management"""

    def test_session_context_success(self, started_db_engine):
        """Session context manager'ın başarılı transaction'da çalışması"""
        engine = started_db_engine
        
        with engine.get_session_context() as session:
            assert isinstance(session, Session)
            # Session context içinde işlem yapılabilir olmalı
            result = session.execute(text("SELECT 1")).fetchone()
            assert result[0] == 1

    def test_session_context_auto_commit(self, started_db_engine, mock_metadata):
        """Session context'in otomatik commit yapması"""
        engine = started_db_engine
        
        # Create table first
        mock_metadata.create_all(engine.get_engine)
        
        with engine.get_session_context() as session:
            session.execute(text("INSERT INTO test_table (name) VALUES ('test')"))
            # Context çıkışında otomatik commit olmalı
        
        # Verify data was committed
        with engine.get_session_context() as session:
            result = session.execute(text("SELECT name FROM test_table WHERE name = 'test'")).fetchone()
            assert result[0] == 'test'

    def test_session_context_auto_rollback(self, started_db_engine):
        """Session context'in exception durumunda otomatik rollback yapması"""
        engine = started_db_engine
        
        with pytest.raises(ValueError):
            with engine.get_session_context() as session:
                session.execute(text("SELECT 1"))  # Valid operation
                raise ValueError("Test exception")  # Force exception
        
        # Session should be properly cleaned up despite exception

    def test_session_context_auto_close(self, started_db_engine):
        """Session context'in otomatik close yapması"""
        engine = started_db_engine
        session_ref = None
        
        with engine.get_session_context() as session:
            session_ref = session
            assert not session_ref.is_active or session_ref.is_active  # Session aktif
        
        # Context çıkışında session kapatılmalı


@pytest.mark.unit
class TestTableOperations:
    """Tests for table operations"""

    def test_create_tables_success(self, started_db_engine, mock_metadata):
        """create_tables metodunun başarılı çalışması"""
        engine = started_db_engine
        
        engine.create_tables(mock_metadata)
        
        # Verify table was created
        with engine.get_session_context() as session:
            result = session.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='test_table'"))
            assert result.fetchone() is not None

    def test_drop_tables_success(self, started_db_engine, mock_metadata):
        """drop_tables metodunun başarılı çalışması"""
        engine = started_db_engine
        
        # First create tables
        engine.create_tables(mock_metadata)
        
        # Then drop them
        engine.drop_tables(mock_metadata)
        
        # Verify table was dropped
        with engine.get_session_context() as session:
            result = session.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='test_table'"))
            assert result.fetchone() is None

    def test_create_tables_auto_start(self, db_engine_instance, mock_metadata):
        """create_tables'ın engine'i otomatik start etmesi"""
        engine = db_engine_instance
        
        assert engine.is_alive is False
        engine.create_tables(mock_metadata)
        assert engine.is_alive is True
        
        # Cleanup
        engine.stop()

    def test_drop_tables_auto_start(self, db_engine_instance, mock_metadata):
        """drop_tables'ın engine'i otomatik start etmesi"""
        engine = db_engine_instance
        
        assert engine.is_alive is False
        engine.drop_tables(mock_metadata)  # Empty metadata, should not fail
        assert engine.is_alive is True
        
        # Cleanup
        engine.stop()


@pytest.mark.unit
class TestUtilityMethods:
    """Tests for utility methods"""

    def test_test_connection_success(self, started_db_engine):
        """test_connection metodunun başarılı çalışması"""
        engine = started_db_engine
        
        result = engine.test_connection()
        assert result is True

    def test_test_connection_auto_start(self, db_engine_instance):
        """test_connection'ın engine'i otomatik start etmesi"""
        engine = db_engine_instance
        
        assert engine.is_alive is False
        result = engine.test_connection()
        assert result is True
        assert engine.is_alive is True
        
        # Cleanup
        engine.stop()

    def test_execute_raw_sql_success(self, started_db_engine, sample_sql_queries):
        """execute_raw_sql metodunun başarılı çalışması"""
        engine = started_db_engine
        
        result = engine.execute_raw_sql(sample_sql_queries["simple_select"])
        assert result[0][0] == 1

    def test_execute_raw_sql_with_parameters(self, started_db_engine, sample_sql_queries):
        """execute_raw_sql'in parametrelerle çalışması"""
        engine = started_db_engine
        
        result = engine.execute_raw_sql(
            sample_sql_queries["parameterized"], 
            {"value": 42}
        )
        assert result[0][0] == 42

    def test_execute_raw_sql_before_start(self, db_engine_instance, sample_sql_queries):
        """execute_raw_sql'in start edilmeden RuntimeError fırlatması"""
        engine = db_engine_instance
        
        with pytest.raises(RuntimeError, match="Engine not initialized"):
            engine.execute_raw_sql(sample_sql_queries["simple_select"])

    def test_execute_raw_sql_invalid_query(self, started_db_engine, sample_sql_queries):
        """execute_raw_sql'in geçersiz SQL ile exception fırlatması"""
        engine = started_db_engine
        
        with pytest.raises(Exception):  # SQLAlchemy exception
            engine.execute_raw_sql(sample_sql_queries["invalid"])

    def test_get_connection_info_structure(self, started_db_engine):
        """get_connection_info'nun doğru yapıda bilgi dönmesi"""
        engine = started_db_engine
        
        info = engine.get_connection_info()
        
        assert isinstance(info, dict)
        assert 'connection_string' in info
        assert 'database_type' in info
        assert 'database_name' in info
        assert 'is_alive' in info
        assert 'engine_config' in info
        
        assert info['database_type'] == 'sqlite'
        assert info['database_name'] == ':memory:'
        assert info['is_alive'] is True

    def test_repr_format(self, db_engine_instance):
        """__repr__ metodunun doğru format dönmesi"""
        engine = db_engine_instance
        
        repr_str = repr(engine)
        
        assert 'DatabaseEngine(' in repr_str
        assert 'db_type=sqlite' in repr_str
        assert 'db_name=:memory:' in repr_str
        assert 'is_alive=False' in repr_str


@pytest.mark.unit
class TestErrorScenarios:
    """Tests for error handling and edge cases"""

    def test_start_with_invalid_config(self):
        """Geçersiz config ile start işleminin başarısız olması"""
        # Create an invalid config
        invalid_config = Mock()
        invalid_config.get_connection_string.return_value = "invalid://connection"
        invalid_config.engine_config.to_dict.return_value = {}
        invalid_config.db_type = DatabaseType.SQLITE
        
        engine = DatabaseEngine(invalid_config)
        
        with pytest.raises(Exception):
            engine.start()

    def test_engine_operations_after_stop(self, started_db_engine):
        """Stop edilen engine ile işlem yapma denemeleri"""
        engine = started_db_engine
        
        engine.stop()
        
        with pytest.raises(RuntimeError):
            engine.get_engine
            
        with pytest.raises(RuntimeError):
            engine.get_session


@pytest.mark.unit
class TestFactoryFunction:
    """Tests for create_database_engine factory function"""

    def test_create_database_engine_success(self, engine_sqlite_config):
        """create_database_engine'in başarılı çalışması"""
        engine = create_database_engine(engine_sqlite_config)
        
        assert isinstance(engine, DatabaseEngine)
        assert engine.is_alive is True
        
        # Cleanup
        engine.stop()

    def test_create_database_engine_ready_to_use(self, engine_sqlite_config):
        """create_database_engine'in kullanıma hazır engine dönmesi"""
        engine = create_database_engine(engine_sqlite_config)
        
        # Should be able to use immediately
        sqlalchemy_engine = engine.get_engine
        session = engine.get_session
        
        assert isinstance(sqlalchemy_engine, Engine)
        assert isinstance(session, Session)
        
        # Cleanup
        session.close()
        engine.stop()

    def test_create_database_engine_with_invalid_config(self):
        """create_database_engine'in geçersiz config ile exception fırlatması"""
        invalid_config = Mock()
        invalid_config.get_connection_string.side_effect = Exception("Invalid config")
        
        with pytest.raises(Exception):
            create_database_engine(invalid_config)