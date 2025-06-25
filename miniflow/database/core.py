from .config import DatabaseConnection, DatabaseConfig, USE_SQLITE
from .schema import Base
from .exceptions import Result

def init_database(db_path_or_url):
    try:
        config = DatabaseConfig(db_path_or_url)
        Base.metadata.create_all(bind=config.get_engine())
        return Result.success({
            "database_initialized": True,
            "message": f"Database created at {db_path_or_url}"
        })
    except Exception as e:
        return Result.error(f"Failed to initialize database: {str(e)}")


def drop_all_tables(db_path_or_url):
    try:
        config = DatabaseConfig(db_path_or_url)
        Base.metadata.drop_all(bind=config.get_engine())
        return Result.success({
            "tables_dropped": True
        })
    except Exception as e:
        return Result.error(f"Failed to drop tables: {str(e)}")


def check_database_connection(db_path_or_url):
    try:
        with DatabaseConnection(db_path_or_url) as session:
            # PostgreSQL'de hata vermemesi için text() kullanılmalı
            from sqlalchemy import text
            session.execute(text("SELECT 1"))
        return Result.success(data={"connection_status": True})
    except Exception as e:
        return Result.error(f"Connection test failed: {str(e)}")


def get_table_info(db_path_or_url, table_class):
    try:
        columns = []
        for column in table_class.__table__.columns:
            columns.append({
                "name": column.name,
                "type": str(column.type),
                "nullable": column.nullable,
                "default": str(column.default),
                "primary_key": column.primary_key
            })

        return Result.success({
            "table_name": table_class.__tablename__,
            "columns": columns,
            "column_count": len(columns)
        })
    except Exception as e:
        return Result.error(f"Failed to get table info: {str(e)}")


def get_all_table_info(db_path_or_url):
    try:
        from . import schema
        results = {}
        for attr in dir(schema):
            obj = getattr(schema, attr)
            if hasattr(obj, "__tablename__"):
                info = get_table_info(db_path_or_url, obj)
                results[obj.__tablename__] = info.data if info.success else {"error": info.error}
        return Result.success(results)
    except Exception as e:
        return Result.error(f"Failed to get all table info: {str(e)}")
