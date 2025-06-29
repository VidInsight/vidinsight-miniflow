from sqlalchemy.pool import QueuePool
from sqlalchemy import text
from .base import BaseDatabaseAdapter

from ..core.config import DatabaseConfig


class MySQLAdapter(BaseDatabaseAdapter):
    """MySQL/MariaDB için optimize edilmiş adapter"""
    
    def get_pool_class(self):
        return QueuePool
    
    def get_optimized_config(self) -> DatabaseConfig:
        """MySQL için optimizasyonlar"""
        optimized = self.config
        
        # MySQL için aggressive pool settings
        optimized.pool_recycle = 3600  # 1 saatte bir yenile
        optimized.pool_pre_ping = True  # Mutlaka ping yap
        
        # MySQL için özel connect_args
        optimized.connect_args.update({
            'charset': 'utf8mb4',
            'connect_timeout': 15,
            'read_timeout': 30,
            'write_timeout': 30,
            'sql_mode': 'STRICT_TRANS_TABLES,NO_ZERO_DATE,NO_ZERO_IN_DATE,ERROR_FOR_DIVISION_BY_ZERO',
        })
        
        return optimized
    
    def get_health_check_query(self) -> str:
        return "SELECT 1"
    
    def optimize_mysql_settings(self):
        """MySQL-specific optimizations"""
        with self.engine.connect() as conn:
            # Connection encoding
            conn.execute(text("SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci"))
            # Timezone
            conn.execute(text("SET time_zone = '+00:00'"))