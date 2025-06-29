# Database Manager - Complete Enterprise-Grade Database System
# =============================================================

# Core components
from .core.manager import DatabaseManager, get_database_manager
from .core.config import DatabaseConfig

# Models (ORM)
from .models import (
    Workflow, Node, Edge, Execution, 
    ExecutionInput, ExecutionOutput, Trigger
)

# Repositories (Data Access Layer)
from .repositories import (
    BaseRepository, WorkflowRepository, NodeRepository, 
    EdgeRepository, ExecutionRepository, ExecutionInputRepository,
    ExecutionOutputRepository, TriggerRepository
)

# Services (Business Logic Layer)
from .services import (
    WorkflowService, ExecutionService, OrchestrationService
)

# Database adapters - Fixed naming to match actual exports
from .adapters import DatabaseAdapter, SqliteAdapter, MySQLAdapter, PostgreSQLAdapter

# Exceptions
from .exceptions import DatabaseManagerError

__version__ = "1.0.0"

__all__ = [
    # Core
    "DatabaseManager",
    "get_database_manager", 
    "DatabaseConfig",
    
    # Models
    "Workflow",
    "Node", 
    "Edge",
    "Execution",
    "ExecutionInput",
    "ExecutionOutput", 
    "Trigger",
    
    # Repositories
    "BaseRepository",
    "WorkflowRepository",
    "NodeRepository",
    "EdgeRepository", 
    "ExecutionRepository",
    "ExecutionInputRepository",
    "ExecutionOutputRepository",
    "TriggerRepository",
    
    # Services
    "WorkflowService",
    "ExecutionService",
    "OrchestrationService",
    
    # Adapters - Fixed naming
    "DatabaseAdapter",
    "SqliteAdapter", 
    "MySQLAdapter",
    "PostgreSQLAdapter",
    
    # Exceptions
    "DatabaseManagerError"
] 