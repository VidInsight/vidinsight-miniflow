from sqlalchemy.pool import StaticPool
from sqlalchemy import text
from .base import BaseDatabaseAdapter

from ..core.config import DatabaseConfig


class SqliteAdapter(BaseDatabaseAdapter):
    """SQLite veritabanı adaptörü"""

    def get_pool_class(self):
        return StaticPool

    def get_optimized_config(self) -> DatabaseConfig:
        """SQLite için optimizasyonlar"""
        # SQLite için özel ayarlar
        optimized = self.config
        
        # SQLite tek thread'li, pool boyutunu küçült
        optimized.pool_size = 1
        optimized.max_overflow = 0
        
        # SQLite için özel connect_args
        optimized.connect_args.update({
            'check_same_thread': False,
            'timeout': 20,
            'isolation_level': None,  # Autocommit mode
        })
        
        return optimized
    
    def get_health_check_query(self) -> str:
        return "SELECT 1"
    
    def enable_wal_mode(self):
        """WAL mode'u etkinleştir - performans için"""
        with self.engine.connect() as conn:
            conn.execute(text("PRAGMA journal_mode=WAL"))
            conn.execute(text("PRAGMA synchronous=NORMAL"))
            conn.execute(text("PRAGMA cache_size=10000"))
            conn.execute(text("PRAGMA temp_store=MEMORY"))