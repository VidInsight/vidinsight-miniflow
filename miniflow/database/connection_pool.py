"""
SQLite Connection Pool for Parallel Database Operations

This module provides a thread-safe connection pool to enable
true parallel database operations within SQLite limitations.
"""

import sqlite3
import threading
import queue
import time
from contextlib import contextmanager
from typing import Optional, Dict, Any
from .exceptions import DatabaseError, Result
from ..utils.logger import logger


class SQLiteConnectionPool:
    """
    Thread-safe SQLite connection pool for parallel operations
    
    Features:
    - WAL mode for better concurrency
    - Connection per thread
    - Bulk transaction support
    - Prepared statement caching
    - Connection health monitoring
    """
    
    def __init__(self, db_path: str, max_connections: int = 10, timeout: float = 30.0):
        self.db_path = db_path
        self.max_connections = max_connections
        self.timeout = timeout
        
        # Thread-safe connection pool
        self._pool = queue.Queue(maxsize=max_connections)
        self._all_connections = []
        self._lock = threading.Lock()
        self._thread_local = threading.local()
        
        # Initialize pool
        self._initialize_pool()
        
        # Performance monitoring
        self._connection_stats = {
            'total_requests': 0,
            'pool_hits': 0,
            'pool_misses': 0,
            'active_connections': 0
        }
    
    def _initialize_pool(self):
        """Initialize connection pool with WAL mode and optimizations"""
        logger.info(f"Initializing SQLite connection pool: {self.max_connections} connections")
        
        # Create initial connections
        for i in range(self.max_connections):
            conn = self._create_connection()
            if conn:
                self._pool.put(conn)
                self._all_connections.append(conn)
    
    def _create_connection(self) -> Optional[sqlite3.Connection]:
        """Create optimized SQLite connection"""
        try:
            # Create connection with optimizations
            conn = sqlite3.connect(
                self.db_path,
                timeout=self.timeout,
                check_same_thread=False,  # Allow cross-thread usage
                isolation_level=None      # Autocommit mode for better concurrency
            )
            
            # Enable WAL mode for better concurrency
            conn.execute("PRAGMA journal_mode=WAL")
            
            # Performance optimizations
            conn.execute("PRAGMA synchronous=NORMAL")      # Faster than FULL
            conn.execute("PRAGMA cache_size=10000")        # 10MB cache
            conn.execute("PRAGMA temp_store=MEMORY")       # Use memory for temp
            conn.execute("PRAGMA mmap_size=268435456")     # 256MB memory map
            conn.execute("PRAGMA page_size=4096")          # Optimal page size
            
            # Enable foreign keys
            conn.execute("PRAGMA foreign_keys=ON")
            
            # Row factory for dict-like access
            conn.row_factory = sqlite3.Row
            
            logger.debug(f"Created optimized SQLite connection: WAL mode enabled")
            return conn
            
        except Exception as e:
            logger.error(f"Failed to create SQLite connection: {e}")
            return None
    
    @contextmanager
    def get_connection(self):
        """Get connection from pool with context manager"""
        conn = None
        try:
            # Try to get connection from pool
            try:
                conn = self._pool.get(timeout=5.0)  # 5 second timeout
                self._connection_stats['pool_hits'] += 1
            except queue.Empty:
                # Pool exhausted, create new connection
                conn = self._create_connection()
                self._connection_stats['pool_misses'] += 1
                if not conn:
                    raise DatabaseError("Failed to create database connection")
            
            self._connection_stats['total_requests'] += 1
            self._connection_stats['active_connections'] += 1
            
            yield conn
            
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            raise
        finally:
            # Return connection to pool
            if conn:
                try:
                    # Health check
                    conn.execute("SELECT 1").fetchone()
                    self._pool.put(conn, timeout=1.0)
                except (queue.Full, sqlite3.Error):
                    # Pool full or connection unhealthy, close it
                    try:
                        conn.close()
                    except:
                        pass
                
                self._connection_stats['active_connections'] -= 1
    
    def get_thread_local_connection(self) -> sqlite3.Connection:
        """Get thread-local connection for long-running operations"""
        if not hasattr(self._thread_local, 'connection'):
            self._thread_local.connection = self._create_connection()
            if not self._thread_local.connection:
                raise DatabaseError("Failed to create thread-local connection")
        
        return self._thread_local.connection
    
    def execute_bulk_transaction(self, operations: list) -> Result:
        """Execute multiple operations in a single transaction"""
        if not operations:
            return Result.success([])
        
        with self.get_connection() as conn:
            try:
                # Start transaction
                conn.execute("BEGIN IMMEDIATE")
                
                results = []
                for operation in operations:
                    query = operation.get('query', '')
                    params = operation.get('params', ())
                    
                    if operation.get('type') == 'select':
                        cursor = conn.execute(query, params)
                        results.append(cursor.fetchall())
                    else:
                        cursor = conn.execute(query, params)
                        results.append(cursor.rowcount)
                
                # Commit transaction
                conn.commit()
                
                logger.debug(f"Bulk transaction completed: {len(operations)} operations")
                return Result.success(results)
                
            except Exception as e:
                # Rollback on error
                try:
                    conn.rollback()
                except:
                    pass
                logger.error(f"Bulk transaction failed: {e}")
                return Result.error(f"Bulk transaction failed: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics"""
        return {
            **self._connection_stats,
            'pool_size': self._pool.qsize(),
            'max_connections': self.max_connections,
            'total_connections': len(self._all_connections)
        }
    
    def close_all(self):
        """Close all connections in pool"""
        logger.info("Closing all database connections")
        
        # Close pooled connections
        while not self._pool.empty():
            try:
                conn = self._pool.get_nowait()
                conn.close()
            except (queue.Empty, sqlite3.Error):
                pass
        
        # Close all tracked connections
        for conn in self._all_connections:
            try:
                conn.close()
            except sqlite3.Error:
                pass
        
        self._all_connections.clear()
        
        # Close thread-local connections
        if hasattr(self._thread_local, 'connection'):
            try:
                self._thread_local.connection.close()
            except sqlite3.Error:
                pass


# Global connection pool instance
_connection_pool = None
_pool_lock = threading.Lock()


def get_connection_pool(db_path: str) -> SQLiteConnectionPool:
    """Get or create global connection pool"""
    global _connection_pool
    
    with _pool_lock:
        if _connection_pool is None:
            _connection_pool = SQLiteConnectionPool(db_path)
        return _connection_pool


def initialize_connection_pool(db_path: str, max_connections: int = 10):
    """Initialize global connection pool"""
    global _connection_pool
    
    with _pool_lock:
        if _connection_pool is not None:
            _connection_pool.close_all()
        
        _connection_pool = SQLiteConnectionPool(db_path, max_connections)
        logger.info(f"Initialized connection pool with {max_connections} connections")


def close_connection_pool():
    """Close global connection pool"""
    global _connection_pool
    
    with _pool_lock:
        if _connection_pool is not None:
            _connection_pool.close_all()
            _connection_pool = None 