from abc import ABC, abstractmethod
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

from ..core.config import DatabaseConfig


class BaseDatabaseAdapter(ABC):
    def __init__(self, config: DatabaseConfig):
        self.engine = None
        self.config = config

    @abstractmethod
    def get_pool_class(self):
        pass

    @abstractmethod
    def get_optimized_config(self):
        pass

    @abstractmethod
    def get_health_check_query(self):
        pass

    def create_engine(self):
        optimized_config = self.get_optimized_config()
        pool_class = self.get_pool_class()

        engine_args = {
            'poolclass': pool_class,
            'echo': optimized_config.echo,
            'echo_pool': optimized_config.echo_pool,
            'connect_args': optimized_config.connect_args,
        }

        if pool_class != StaticPool:
            engine_args.update({
                'pool_size': optimized_config.pool_size,
                'max_overflow': optimized_config.max_overflow,
                'pool_timeout': optimized_config.pool_timeout,
                'pool_recycle': optimized_config.pool_recycle,
                'pool_pre_ping': optimized_config.pool_pre_ping,
            })
        else:
            # StaticPool only supports these parameters
            if hasattr(optimized_config, 'pool_pre_ping') and optimized_config.pool_pre_ping:
                engine_args['pool_pre_ping'] = optimized_config.pool_pre_ping
        
        self.engine = create_engine(
            optimized_config.url,
            **engine_args
        )
        
        return self.engine

    def validate_connection(self) -> bool:
        """Bağlantıyı test et"""
        try:
            with self.engine.connect() as conn:
                conn.execute(text(self.get_health_check_query()))
            return True
        except Exception as e:
            print(f"Connection validation failed: {e}")
            return False    