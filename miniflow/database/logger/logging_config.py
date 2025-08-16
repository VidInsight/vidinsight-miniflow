"""
MINIFLOW DATABASE LOGGING CONFIGURATION
========================================

Database modülü için merkezi logging konfigürasyonu.
Environment variables ile kontrol edilebilir.
"""

import os
import logging
import logging.config
import logging.handlers
from enum import Enum
from typing import Dict, Any, Optional


# Logging Levels
class LogLevel(Enum):
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL

# Logging Format
class LogFormat(Enum):
    STRUCTURED = "structured"   # Production için structured logging
    SIMPLE = "simple"           # Development için basit format
    JSON = "json"               # JSON formatı  


class DatabaseLoggingConfig:
    "Database modülü için logging konfigürasyonu"

    def __init__(self):
        # Environment variables'dan konfigürasyon al
        self.log_level = os.getenv("MINIFLOW_DB_LOG_LEVEL", "INFO")
        self.log_format = os.getenv("MINIFLOW_DB_LOG_FORMAT", "simple")
        self.log_file_path = os.getenv("MINIFLOW_DB_LOG_FILE", None)
        
        # Feature flags
        self.enable_performance_logs = os.getenv("MINIFLOW_DB_PERF_LOGS", "true").lower() == "true"
        self.enable_sql_logs = os.getenv("MINIFLOW_DB_SQL_LOGS", "false").lower() == "true"
        self.enable_audit_logs = os.getenv("MINIFLOW_DB_AUDIT_LOGS", "true").lower() == "true"
        
        # Advanced settings
        self.max_log_file_size = int(os.getenv("MINIFLOW_DB_LOG_MAX_SIZE", "10485760"))  # 10MB
        self.log_backup_count = int(os.getenv("MINIFLOW_DB_LOG_BACKUP_COUNT", "5"))
    
    def get_logging_config(self) -> Dict[str, Any]:
        """Logging konfigürasyonunu 'DICT' olarak döndürür"""

        handlers = ["console"]
        if self.log_file_path:
            handlers.append('file')
            handlers.append('rotating_file')

        config = {
            'version': 1,
            'disable_existing_loggers': False,
            'formatters': {
                'structured': {
                    'format': '%(asctime)s | %(name)s | %(levelname)s | %(component)s | %(operation)s | %(message)s',
                    'datefmt': '%Y-%m-%d %H:%M:%S'
                },
                'simple': {
                    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    'datefmt': '%Y-%m-%d %H:%M:%S'
                },
                'detailed': {
                    'format': '[%(asctime)s] %(name)s.%(funcName)s:%(lineno)d - %(levelname)s - %(message)s',
                    'datefmt': '%Y-%m-%d %H:%M:%S'
                }
            },
            
            'handlers': {
                'console': {
                    'class': 'logging.StreamHandler',
                    'level': 'DEBUG',
                    'formatter': self.log_format,
                    'stream': 'ext://sys.stdout'
                }
            },
            
            'loggers': {
                'miniflow.database': {
                    'level': self.log_level,
                    'handlers': handlers,
                    'propagate': False
                },
                'miniflow.database.engine': {
                    'level': self.log_level,
                    'handlers': handlers,
                    'propagate': False
                },
                'miniflow.database.orchestration': {
                    'level': self.log_level, 
                    'handlers': handlers,
                    'propagate': False
                },
                'miniflow.database.crud': {
                    'level': self.log_level,
                    'handlers': handlers,
                    'propagate': False
                },
                'miniflow.database.audit': {
                    'level': self.log_level if self.enable_audit_logs else 'WARNING',
                    'handlers': handlers,
                    'propagate': False
                },
                'miniflow.database.performance': {
                    'level': 'DEBUG' if self.enable_performance_logs else 'INFO',
                    'handlers': handlers,
                    'propagate': False
                }
            }
        }
        
        # File handler ekle (eğer path verilmişse)
        if self.log_file_path:
            config['handlers']['file'] = {
                'class': 'logging.FileHandler',
                'level': 'DEBUG',
                'formatter': 'structured',
                'filename': self.log_file_path,
                'mode': 'a'
            }
            
            config['handlers']['rotating_file'] = {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'INFO',
                'formatter': 'structured',
                'filename': f"{self.log_file_path}.rotating",
                'maxBytes': self.max_log_file_size,
                'backupCount': self.log_backup_count
            }
        
        return config

    def configure_logging(self):
        """Logging'i configure et"""
        config = self.get_logging_config()
        logging.config.dictConfig(config)
        
        # SQL logging configuration (eğer enabled ise)
        if self.enable_sql_logs:
            self._configure_sql_logging()
    
    def _configure_sql_logging(self):
        """SQLAlchemy logging'i configure et"""
        sql_logger = logging.getLogger('sqlalchemy.engine')
        sql_logger.setLevel(logging.INFO)
        
        # SQL logger için ayrı handler (opsiyonel)
        if self.log_file_path:
            sql_handler = logging.FileHandler(f"{self.log_file_path}.sql")
            sql_formatter = logging.Formatter(
                '%(asctime)s - SQL - %(levelname)s - %(message)s'
            )
            sql_handler.setFormatter(sql_formatter)
            sql_logger.addHandler(sql_handler)


def get_database_logging_config() -> Dict[str, Any]:
    """Database logging config'i döner (factory function)"""
    config = DatabaseLoggingConfig()
    return config.get_logging_config()


def configure_database_logging():
    """Database logging'i configure et (initialize function)"""
    config = DatabaseLoggingConfig()
    config.configure_logging()
    
    # Configuration bilgilerini log'la
    logger = logging.getLogger('miniflow.database')
    logger.info("Database logging configured", extra={
        'component': 'logging_config',
        'operation': 'configure',
        'log_level': config.log_level,
        'log_format': config.log_format,
        'performance_logs': config.enable_performance_logs,
        'sql_logs': config.enable_sql_logs,
        'audit_logs': config.enable_audit_logs
    })
    
    