import time 
import sqlite3

class DatabaseConfig:
    def __init__(self, db_path):
        self.db_path = db_path
        self.timeout = 30
        self.check_same_thread = False

    def set_timeout(self, timeout):
        self.timeout = timeout

    def set_check_same_thread(self, check_same_thread):
        self.check_same_thread = check_same_thread

    def get_connection(self):
        return DatabaseConnection(
            self.db_path,
            self.timeout,
            self.check_same_thread
        )
    
class DatabaseConnection:
    def __init__(self, db_path, timeout, check_same_thread):
        self.db_path = db_path
        self.timeout = timeout
        self.check_same_thread = check_same_thread

        self.connection = None

    def __enter__(self):
        try: 
            self.connection = sqlite3.connect(
                database=self.db_path,
                check_same_thread=self.check_same_thread,
                timeout=self.timeout
            )
            self.connection.row_factory = sqlite3.Row
            return self.connection
        except sqlite3.Error as e:
            raise ConnectionError(f"Failed to connect to database: {str(e)}")
        
    def __exit__(self, exc_type, exc_val):
        if self.connection:
            try:
                self.connection.close()
            except Exception as e:
                # Log the error but don't raise it
                print(f"Error closing connection: {str(e)}")
        
        if exc_type:
            if isinstance(exc_val, Exception):
                raise exc_val
            raise Exception(f"Database operation failed: {str(exc_val)}")