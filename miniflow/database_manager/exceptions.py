class DatabaseManagerError(Exception):
    """Base exception for database manager"""
    pass

class DatabaseConfigError(DatabaseManagerError):
    """Configuration related errors"""
    pass

class DatabaseConnectionError(DatabaseManagerError):
    """Connection related errors"""
    pass

class DatabasePoolError(DatabaseManagerError):
    """Pool related errors"""
    pass

class DatabaseHealthError(DatabaseManagerError):
    """Health check related errors"""
    pass