from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from enum import Enum


class DatabaseType(Enum):
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    MARIADB = "mariadb"


@dataclass
class DatabaseConfig:
    """Database configuration class with connection and pool settings"""

    # Connection/Bağlantı Bilgileri
    url: str
    db_type: DatabaseType
    """
    url: Database connection URL
    db_type: Type of database (sqlite, postgresql, mysql, mariadb)
    """

    # Pool ayarları - veritabanına göre optimize edilecek
    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout: int = 30
    pool_recycle: int = 3600
    pool_pre_ping: bool = True
    """
    pool_size: Number of connections to maintain in the pool
    max_overflow: Number of connections that can overflow the pool
    pool_timeout: Timeout in seconds for getting connection from pool
    pool_recycle: Time in seconds to recycle connections
    pool_pre_ping: Enable connection health check before use
    """

    # Mesaj/Log ayarları
    echo: bool = False
    echo_pool: bool = False
    """
    echo: Enable SQL query logging
    echo_pool: Enable connection pool logging
    """

    # Connection-specific ayarlar
    connect_args: Dict[str, Any] = field(default_factory=dict)
    """
    connect_args: Database-specific connection arguments
    """

    # Retry ayarları
    max_retries: int = 3
    retry_delay: float = 1.0
    """
    max_retries: Maximum number of connection retry attempts
    retry_delay: Delay in seconds between retries
    """

    # Health check
    health_check_interval: int = 60
    """
    health_check_interval: Interval in seconds for health checks
    """