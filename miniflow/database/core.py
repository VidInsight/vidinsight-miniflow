from functools import wraps
from .config import DatabaseConfig
from .exceptions import Result
from .schema import *
from .connection_pool import get_connection_pool, initialize_connection_pool

# Performance optimized database functions using connection pool
def execute_sql_query(db_path, query, params=None):
    try:
        pool = get_connection_pool(db_path)
        with pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params or ())
            affected_rows = cursor.rowcount
            # Connection pool handles transaction management
            return Result.success(data={"affected_rows": affected_rows})
    except Exception as e:
        return Result.error(error=str(e), metadata={"query": query, "params": params})
    
def fetch_one(db_path, query, params=None):
    try:
        pool = get_connection_pool(db_path)
        with pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params or ())
            row = cursor.fetchone()
            result = dict(row) if row else None
            return Result.success(data=result)
    except Exception as e:
        return Result.error(error=str(e), metadata={"query": query, "params": params})
            
def fetch_all(db_path, query, params=None):
    try:
        pool = get_connection_pool(db_path)
        with pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params or ())
            rows = cursor.fetchall()
            result = [dict(row) for row in rows]
            return Result.success(data=result)
    except Exception as e:
        return Result.error(error=str(e), metadata={"query": query, "params": params})
    
def check_database_connection(db_path):
    try:
        pool = get_connection_pool(db_path)
        with pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            return Result.success(data={
                "connection_status": bool(result), 
                "db_path": db_path,
                "test_result": result[0] if result else None,
                "pool_stats": pool.get_stats()})
    except Exception as e:
        return Result.error(error=str(e), metadata={"db_path": db_path})

def handle_db_errors(operation_name: str):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                return Result.error(f"Failed to {operation_name}: {str(e)}")
        return wrapper
    return decorator 

# Veritabanı fonksiyonları
def create_all_tables(db_path):
    try:
        created_tables = []
        for table_name, table_sql in ALL_TABLES:
            result = execute_sql_query(db_path=db_path, query=table_sql, params=None)
            if not result.success:
                return Result.error(f"Failed to create table {table_name}: {result.error}")

            created_tables.append(table_name)

        return Result.success({
            "tables_created": created_tables,
            "table_count": len(created_tables)
        })
    
    except Exception as e:
        return Result.error(f"Failed to create tables: {str(e)}")
    
def create_all_indexes(db_path):
    try:
        created_indexes = 0

        for index_sql in INDEXES:
            result = execute_sql_query(db_path=db_path, query=index_sql, params=None)
            if not result.success:
                return Result.error(f"Failed to create index: {result.error}")
            created_indexes += 1
        
        return Result.success({
            "indexes_created": created_indexes
        })
        
    except Exception as e:
        return Result.error(f"Failed to create indexes: {str(e)}")
    
def drop_all_tables(db_path):
    try:
        dropped_tables = []

        for table_name, _ in reversed(ALL_TABLES):
            result = execute_sql_query(db_path=db_path, query=f"DROP TABLE IF EXISTS {table_name}", params=None)
            if not result.success:
                return Result.error(f"Failed to drop table {table_name}: {result.error}")
            dropped_tables.append(table_name)
        
        return Result.success({
            "tables_dropped": dropped_tables,
            "table_count": len(dropped_tables)
        })
        
    except Exception as e:
        return Result.error(f"Failed to drop tables: {str(e)}")
    
def check_schema(db_path):
    try:
        result = fetch_all(db_path, "SELECT name FROM sqlite_master WHERE type='table'")

        if not result.success:
            return result
        
        existing_tables = [row["name"] for row in result.data]
        required_tables = [table_name for table_name, _ in ALL_TABLES]
        missing_tables = [table for table in required_tables if table not in existing_tables]
        
        return Result.success({
            "existing_tables": existing_tables,
            "required_tables": required_tables, 
            "missing_tables": missing_tables,
            "schema_complete": len(missing_tables) == 0,
            "table_count": len(existing_tables)
        })
        
    except Exception as e:
        return Result.error(f"Failed to check schema: {str(e)}")

def get_table_info(db_path, table_name):
     try:
        result = fetch_all(db_path, f"PRAGMA table_info({table_name})")
        
        if not result.success:
            return result
        
        columns = []
        for row in result.data:
            columns.append({
                "name": row["name"],
                "type": row["type"],
                "not_null": bool(row["notnull"]),
                "default_value": row["dflt_value"],
                "primary_key": bool(row["pk"])
            })
        
        return Result.success({
            "table_name": table_name,
            "columns": columns,
            "column_count": len(columns)
        })
     
     except Exception as e:
        return Result.error(f"Failed to get table info for {table_name}: {str(e)}")
     
def get_all_table_info(db_path):

    try:
        table_info = {}
        
        for table_name, _ in ALL_TABLES:
            info_result = get_table_info(db_path, table_name)
            if info_result.success:
                table_info[table_name] = info_result.data
            else:
                table_info[table_name] = {"error": info_result.error}
        
        return Result.success(table_info)
        
    except Exception as e:
        return Result.error(f"Failed to get all table info: {str(e)}")
    
def init_database(db_path):
    try: 
        # Initialize connection pool first for better performance
        initialize_connection_pool(db_path, max_connections=10)
        
        # Adım 1: Tabloları oluştur
        table_result = create_all_tables(db_path)
        if not table_result.success:
            return table_result
        
        # Adım 2: İndekleri oluştur
        index_result = create_all_indexes(db_path)
        if not index_result.success:
            return index_result
        
        # Adım 3: Çıktıyı oluştur
        return Result.success({
            "tables_created": len(ALL_TABLES),
            "indexes_created": len(INDEXES),
            "database_initialized": True
        })
        
    except Exception as e:
        return Result.error(f"Failed to initialize database: {str(e)}")

def execute_bulk_operations(db_path, operations):
    """Execute multiple operations in a single transaction for better performance"""
    try:
        pool = get_connection_pool(db_path)
        return pool.execute_bulk_transaction(operations)
    except Exception as e:
        return Result.error(error=str(e), metadata={"operations_count": len(operations)})