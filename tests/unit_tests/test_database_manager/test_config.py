import pytest

from miniflow.database_manager.config import DatabaseType, DatabaseConfig, EngineConfig, get_database_config
from miniflow.database_manager.config import get_sqlite_config, get_postgresql_config, get_mysql_config
from miniflow.database_manager.config import DB_ENGINE_CONFIGS


class TestDatabaseType:
    """DatabaseType enum testleri"""
    def test_database_type_values(self):
        """Enum değerlerinin doğru olduğunu test eder"""
        assert DatabaseType.SQLITE.value == "sqlite"
        assert DatabaseType.MYSQL.value == "mysql"
        assert DatabaseType.POSTGRESQL.value == "postgresql"

    def test_database_type_count(self):
        """Enum'da beklenen sayıda değer olduğunu test eder"""
        assert len(DatabaseType) == 3

class TestEngineConfig:
    """EngineConfig sınıfı testleri"""

    def test_engine_config_default_values(self, default_engine_config):
        """Default değerlerin doğru ayarlandığını test eder"""
        assert default_engine_config.pool_size == 10
        assert default_engine_config.max_overflow == 20
        assert default_engine_config.pool_timeout == 30
        assert default_engine_config.pool_recycle == 3600
        assert default_engine_config.pool_pre_ping == True
        assert default_engine_config.echo == False
        assert default_engine_config.echo_pool == False
        assert default_engine_config.autocommit == False
        assert default_engine_config.autoflush == True
        assert default_engine_config.expire_on_commit == True
        assert default_engine_config.isolation_level is None
        assert default_engine_config.connect_args == {}

    def test_engine_config_custom_values(self, custom_engine_config):
        """Custom değerlerle EngineConfig oluşturulmasını test eder"""
        assert custom_engine_config.pool_size == 5
        assert custom_engine_config.max_overflow == 10
        assert custom_engine_config.echo == True
        assert custom_engine_config.isolation_level == "READ_COMMITTED"
        assert custom_engine_config.connect_args == {"charset": "utf8mb4", "timeout": 30}

    def test_engine_config_to_dict(self, minimal_engine_config):
        """to_dict metodunun doğru çalıştığını test eder"""
        result = minimal_engine_config.to_dict()
        expected = {
            'pool_size': 1,
            'max_overflow': 20,  # default
            'pool_timeout': 30,  # default
            'pool_recycle': 3600,  # default
            'pool_pre_ping': True,  # default
            'connect_args': {},
            'echo': True,
            'echo_pool': False,  # default
            'isolation_level': 'SERIALIZABLE',
        }

        assert result == expected

    def test_engine_config_with_all_fields(self):
        """Tüm field'ların doğru çalıştığını test eder"""
        config = EngineConfig(
            pool_size=25,
            max_overflow=50,
            pool_timeout=120,
            pool_recycle=7200,
            pool_pre_ping=False,
            echo=True,
            echo_pool=True,
            autocommit=True,
            autoflush=False,
            expire_on_commit=False,
            isolation_level="SERIALIZABLE",
            connect_args={"test": "value", "timeout": 60}
        )

        assert config.pool_size == 25
        assert config.max_overflow == 50
        assert config.pool_timeout == 120
        assert config.pool_recycle == 7200
        assert config.pool_pre_ping == False
        assert config.echo == True
        assert config.echo_pool == True
        assert config.autocommit == True
        assert config.autoflush == False
        assert config.expire_on_commit == False
        assert config.isolation_level == "SERIALIZABLE"
        assert config.connect_args == {"test": "value", "timeout": 60}

    def test_engine_config_edge_cases(self):
        """Edge case'leri test eder"""
        # Zero values
        config = EngineConfig(pool_size=0, max_overflow=0)
        assert config.pool_size == 0
        assert config.max_overflow == 0

        # Negative values (should work)
        config = EngineConfig(pool_size=-1, max_overflow=-5)
        assert config.pool_size == -1
        assert config.max_overflow == -5

        # None values
        config = EngineConfig(isolation_level=None)
        assert config.isolation_level is None

        # Empty connect_args
        config = EngineConfig(connect_args={})
        assert config.connect_args == {}

class TestDatabaseConfig:
    """DatabaseConfig sınıfı testleri"""

    def test_database_config_default_values(self, empty_database_config):
        """Default değerlerin doğru ayarlandığını test eder"""
        assert empty_database_config.db_name is None
        assert empty_database_config.db_type is None
        assert empty_database_config.host is None
        assert empty_database_config.port is None
        assert empty_database_config.username is None
        assert empty_database_config.password is None
        assert isinstance(empty_database_config.engine_config, EngineConfig)

    def test_sqlite_connection_string(self, sqlite_database_config, sample_connection_strings):
        """SQLite connection string oluşturulmasını test eder"""
        connection_string = sqlite_database_config.get_connection_string()
        assert connection_string == sample_connection_strings["sqlite"]

    def test_mysql_connection_string(self, mysql_database_config, sample_connection_strings):
        """MySQL connection string oluşturulmasını test eder"""
        connection_string = mysql_database_config.get_connection_string()
        assert connection_string == sample_connection_strings["mysql"]

    def test_postgresql_connection_string(self, postgresql_database_config, sample_connection_strings):
        """PostgreSQL connection string oluşturulmasını test eder"""
        connection_string = postgresql_database_config.get_connection_string()
        assert connection_string == sample_connection_strings["postgresql"]

    def test_to_dict_with_password_masked(self, sample_database_configs):
        """to_dict metodunun şifreyi maskelemesini test eder"""
        mysql_config = sample_database_configs["mysql"]
        result = mysql_config.to_dict(mask_password=True)

        assert result['password'] == '***masked***'
        assert result['db_name'] == 'test_db'
        assert result['db_type'] == 'mysql'
        assert result['username'] == 'root'

    def test_to_dict_with_password_unmasked(self, sample_database_configs):
        """to_dict metodunun şifreyi maskelemeden döndürmesini test eder"""
        mysql_config = sample_database_configs["mysql"]
        result = mysql_config.to_dict(mask_password=False)
        assert result['password'] == 'password123'

    def test_to_dict_without_password(self, sample_database_configs):
        """Şifre olmadığında to_dict metodunun çalışmasını test eder"""
        mysql_no_pass_config = sample_database_configs["mysql_without_password"]
        result = mysql_no_pass_config.to_dict()
        assert result['password'] is None

    # Error case tests
    def test_connection_string_unsupported_database_type(self):
        """Desteklenmeyen database türü için hata test eder"""
        config = DatabaseConfig(
            db_name="test_db",
            db_type="unsupported_type"  # Invalid type
        )
        
        with pytest.raises(ValueError, match="Unsupported database type"):
            config.get_connection_string()

    def test_connection_string_none_db_type(self):
        """None db_type ile connection string oluşturma hatası"""
        config = DatabaseConfig(
            db_name="test_db",
            db_type=None
        )
        
        with pytest.raises(ValueError, match="Unsupported database type"):
            config.get_connection_string()

    def test_connection_string_none_db_name(self):
        """None db_name ile connection string oluşturma"""
        config = DatabaseConfig(
            db_name=None,
            db_type=DatabaseType.SQLITE
        )
        
        # Should work but create "None.db"
        connection_string = config.get_connection_string()
        assert connection_string == "sqlite:///None.db"

    def test_database_config_without_engine_config(self):
        """Engine config olmadan DatabaseConfig oluşturma"""
        config = DatabaseConfig(
            db_name="test_db",
            db_type=DatabaseType.SQLITE,
            engine_config=None
        )
        
        assert config.engine_config is None
        # to_dict should handle None engine_config
        result = config.to_dict()
        assert result['engine_config'] is None

    def test_to_dict_with_none_values(self):
        """None değerlerle to_dict metodunu test eder"""
        config = DatabaseConfig(
            db_name=None,
            db_type=None,
            host=None,
            port=None,
            username=None,
            password=None,
            engine_config=None
        )
        
        result = config.to_dict()
        assert result['db_name'] is None
        assert result['db_type'] is None
        assert result['host'] is None
        assert result['port'] is None
        assert result['username'] is None
        assert result['password'] is None
        assert result['engine_config'] is None


class TestDBEngineConfigs:
    """DB_ENGINE_CONFIGS testleri"""

    def test_sqlite_engine_config(self):
        """SQLite engine config değerlerini test eder"""
        sqlite_config = DB_ENGINE_CONFIGS[DatabaseType.SQLITE]
        
        assert sqlite_config.pool_size == 1
        assert sqlite_config.max_overflow == 0
        assert sqlite_config.pool_timeout == 20
        assert sqlite_config.pool_recycle == -1
        assert sqlite_config.pool_pre_ping == False
        assert sqlite_config.isolation_level is None
        assert 'check_same_thread' in sqlite_config.connect_args
        assert 'timeout' in sqlite_config.connect_args

    def test_postgresql_engine_config(self):
        """PostgreSQL engine config değerlerini test eder"""
        postgresql_config = DB_ENGINE_CONFIGS[DatabaseType.POSTGRESQL]
        
        assert postgresql_config.pool_size == 20
        assert postgresql_config.max_overflow == 30
        assert postgresql_config.pool_timeout == 60
        assert postgresql_config.pool_recycle == 3600
        assert postgresql_config.pool_pre_ping == True
        assert postgresql_config.isolation_level == 'READ_COMMITTED'
        assert 'connect_timeout' in postgresql_config.connect_args
        assert 'application_name' in postgresql_config.connect_args

    def test_mysql_engine_config(self):
        """MySQL engine config değerlerini test eder"""
        mysql_config = DB_ENGINE_CONFIGS[DatabaseType.MYSQL]
        
        assert mysql_config.pool_size == 15
        assert mysql_config.max_overflow == 25
        assert mysql_config.pool_timeout == 45
        assert mysql_config.pool_recycle == 7200
        assert mysql_config.pool_pre_ping == True
        assert mysql_config.isolation_level == 'READ_COMMITTED'
        assert 'connect_timeout' in mysql_config.connect_args
        assert 'charset' in mysql_config.connect_args
        assert 'autocommit' in mysql_config.connect_args

    def test_all_database_types_have_configs(self):
        """Tüm database türlerinin config'e sahip olduğunu test eder"""
        for db_type in DatabaseType:
            assert db_type in DB_ENGINE_CONFIGS
            assert isinstance(DB_ENGINE_CONFIGS[db_type], EngineConfig)


class TestGetDatabaseConfig:
    """get_database_config fonksiyonu testleri"""

    def test_get_database_config_with_predefined_engine(self):
        """Önceden tanımlanmış engine config ile test eder"""
        config = get_database_config(
            db_name="test_db",
            db_type=DatabaseType.POSTGRESQL,
            host="localhost",
            port=5432,
            username="postgres",
            password="secret"
        )

        assert config.db_name == "test_db"
        assert config.db_type == DatabaseType.POSTGRESQL
        assert config.host == "localhost"
        assert config.port == 5432
        assert config.username == "postgres"
        assert config.password == "secret"
        assert config.engine_config.pool_size == 20  # PostgreSQL default

    def test_get_database_config_with_custom_engine(self, custom_engine_config):
        """Custom engine config ile test eder"""
        config = get_database_config(
            db_name="test_db",
            db_type=DatabaseType.SQLITE,
            custom_engine_config=custom_engine_config
        )

        assert config.engine_config.pool_size == 5
        assert config.engine_config.echo == True

    def test_get_database_config_unsupported_type_error(self):
        """Desteklenmeyen database türü için hata test eder"""
        with pytest.raises(KeyError, match="No predefined engine config found"):
            get_database_config(
                db_name="test_db",
                db_type="unsupported_type"
            )

    def test_get_database_config_with_none_values(self):
        """None değerlerle config oluşturma"""
        config = get_database_config(
            db_name="test_db",
            db_type=DatabaseType.SQLITE,
            host=None,
            port=None,
            username=None,
            password=None
        )

        assert config.db_name == "test_db"
        assert config.db_type == DatabaseType.SQLITE
        assert config.host is None
        assert config.port is None
        assert config.username is None
        assert config.password is None

    def test_get_database_config_all_database_types(self):
        """Tüm database türleri için config oluşturma"""
        for db_type in DatabaseType:
            config = get_database_config(
                db_name="test_db",
                db_type=db_type
            )
            assert config.db_type == db_type
            assert config.db_name == "test_db"


class TestFactoryFunctions:
    """Factory fonksiyonları testleri"""

    def test_get_sqlite_config_default(self, factory_function_configs):
        """Default SQLite config oluşturulmasını test eder"""
        config = factory_function_configs["sqlite_default"]

        assert config.db_type == DatabaseType.SQLITE
        assert config.db_name == "database.db"
        assert config.host is None
        assert config.username is None
        assert config.engine_config.pool_size == 1  # SQLite default

    def test_get_sqlite_config_custom(self, factory_function_configs):
        """Custom SQLite config oluşturulmasını test eder"""
        config = factory_function_configs["sqlite_custom"]

        assert config.db_name == "custom.db"
        assert config.db_type == DatabaseType.SQLITE

    def test_get_postgresql_config_default(self, factory_function_configs):
        """Default PostgreSQL config oluşturulmasını test eder"""
        config = factory_function_configs["postgresql_default"]

        assert config.db_type == DatabaseType.POSTGRESQL
        assert config.db_name == "postgres"
        assert config.host == "localhost"
        assert config.port == 5432
        assert config.username == "postgres"
        assert config.password == ""
        assert config.engine_config.pool_size == 20  # PostgreSQL default

    def test_get_postgresql_config_custom(self, factory_function_configs):
        """Custom PostgreSQL config oluşturulmasını test eder"""
        config = factory_function_configs["postgresql_custom"]

        assert config.db_name == "custom_db"
        assert config.host == "pg.example.com"
        assert config.port == 5433
        assert config.username == "custom_user"
        assert config.password == "custom_pass"

    def test_get_mysql_config_default(self, factory_function_configs):
        """Default MySQL config oluşturulmasını test eder"""
        config = factory_function_configs["mysql_default"]

        assert config.db_type == DatabaseType.MYSQL
        assert config.db_name == "mysql"
        assert config.host == "localhost"
        assert config.port == 3306
        assert config.username == "root"
        assert config.password == ""
        assert config.engine_config.pool_size == 15  # MySQL default

    def test_get_mysql_config_custom(self, factory_function_configs):
        """Custom MySQL config oluşturulmasını test eder"""
        config = factory_function_configs["mysql_custom"]

        assert config.db_name == "app_db"
        assert config.host == "mysql.example.com"
        assert config.port == 3307
        assert config.username == "app_user"
        assert config.password == "app_pass"

    # Direct factory function tests
    def test_get_sqlite_config_direct(self):
        """get_sqlite_config fonksiyonunu doğrudan test eder"""
        config = get_sqlite_config()
        assert config.db_type == DatabaseType.SQLITE
        assert config.db_name == "database.db"

        config = get_sqlite_config(db_name="test.db")
        assert config.db_name == "test.db"

    def test_get_postgresql_config_direct(self):
        """get_postgresql_config fonksiyonunu doğrudan test eder"""
        config = get_postgresql_config()
        assert config.db_type == DatabaseType.POSTGRESQL
        assert config.db_name == "postgres"
        assert config.host == "localhost"

        config = get_postgresql_config(db_name="test_db", host="test.com")
        assert config.db_name == "test_db"
        assert config.host == "test.com"

    def test_get_mysql_config_direct(self):
        """get_mysql_config fonksiyonunu doğrudan test eder"""
        config = get_mysql_config()
        assert config.db_type == DatabaseType.MYSQL
        assert config.db_name == "mysql"
        assert config.host == "localhost"

        config = get_mysql_config(db_name="test_db", host="test.com")
        assert config.db_name == "test_db"
        assert config.host == "test.com"
