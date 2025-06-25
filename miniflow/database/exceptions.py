# database/exceptions.py
class DatabaseError(Exception):
    """Custom exception for database operations"""
    pass

class Result:
    def __init__(self, success, data=None, error=None, metadata=None):
        self.success = success
        self.data = data
        self.error = error
        self.metadata = metadata or {}

    @classmethod
    def success(cls, data=None, metadata=None):
        return cls(success=True, data=data, metadata=metadata)

    @classmethod
    def error(cls, error, metadata=None):
        return cls(success=False, error=error, metadata=metadata)

    def __bool__(self):
        return self.success

    def __repr__(self):
        return f"Result(success={self.success}, data={self.data}, error={self.error}, metadata={self.metadata})"

    def to_dict(self):
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "metadata": self.metadata
        }
