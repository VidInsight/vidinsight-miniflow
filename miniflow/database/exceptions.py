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
        """Create a successful result"""
        return cls(success=True, data=data, metadata=metadata)
    
    @classmethod
    def failure(cls, error, metadata=None):
        """Create a failed result"""
        return cls(success=False, error=error, metadata=metadata)
    
    def __bool__(self):
        """Return True if the result is successful, False otherwise"""
        return self.success
    
    def __repr__(self):
        """String representation of the Result object"""
        return f"Result(success={self.success}, data={self.data}, error={self.error}, metadata={self.metadata})"
    
    def to_dict(self):
        """Convert the Result object to a dictionary"""
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "metadata": self.metadata
        }