from .config import DatabaseConnection
from .exceptions import Result

def execute_sql_query(db_path, query, params=None):
    try:
        conn = DatabaseConnection(db_path)
        with conn:
            cursor = conn.cursor()
            cursor.execute(query, params or ())
            affected_rows = cursor.rowcount
            conn.commit()

            return Result.success(data={"affected_rows": affected_rows})
    except Exception as e:
        return Result.failure(error=str(e), metadata={"query": query, "params": params})
    
def fetch_one(db_path, query, params=None):
    try:
        conn = DatabaseConnection(db_path)
        with conn:
            cursor = conn.cursor()
            cursor.execute(query, params or ())
            row = cursor.fetchone()

            result = dict(row) if row else None

            return Result.success(data=result)
    except Exception as e:
        return Result.failure(error=str(e), metadata={"query": query, "params": params})
            
def fetch_all(db_path, query, params=None):
    try:
        conn = DatabaseConnection(db_path)
        with conn:
            cursor = conn.cursor()
            cursor.execute(query, params or ())
            rows = cursor.fetchall()

            result = [dict(row) for row in rows]

            return Result.success(data=result)
    except Exception as e:
        return Result.failure(error=str(e), metadata={"query": query, "params": params})
    

def check_database_connection(db_path):
    try:
        conn = DatabaseConnection(db_path)
        with conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            return Result.success(data={
                "connection_status": bool(result), 
                "db_path": db_path,
                "test_result": result[0] if result else None})
    except Exception as e:
        return Result.failure(error=str(e), metadata={"db_path": db_path})