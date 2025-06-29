from sqlalchemy.pool import QueuePool
from sqlalchemy import text
from .base import BaseDatabaseAdapter

from ..core.config import DatabaseConfig


class PostgreSQLAdapter(BaseDatabaseAdapter):
    """PostgreSQL için optimize edilmiş adapter"""
    
    def get_pool_class(self):
        return QueuePool
    
    def get_optimized_config(self) -> DatabaseConfig:
        """PostgreSQL için optimizasyonlar"""
        optimized = self.config
        
        # PostgreSQL robust, daha büyük pool'lar kullanabilir
        if optimized.pool_size < 10:
            optimized.pool_size = 10
        
        optimized.pool_recycle = 7200  # 2 saatte bir yenile
        
        # PostgreSQL için özel connect_args
        optimized.connect_args.update({
            'connect_timeout': 10,
            'application_name': 'sqlalchemy_app',
            'options': '-c timezone=utc'
        })
        
        return optimized
    
    def get_health_check_query(self) -> str:
        return "SELECT 1"
    
    def optimize_postgresql_settings(self):
        """PostgreSQL-specific optimizations"""
        with self.engine.connect() as conn:
            # Timezone
            conn.execute(text("SET timezone = 'UTC'"))
            # Lock timeout
            conn.execute(text("SET lock_timeout = '30s'"))