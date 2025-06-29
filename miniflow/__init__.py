"""
Miniflow - Lightweight Workflow Orchestration Framework

Bu framework workflow yönetimi, task scheduling ve execution monitoring için
temel bileşenler sağlar.

Ana Modüller:
- database: Core database işlemleri ve workflow data management
- scheduler: Task scheduling, monitoring ve execution coordination
"""

# Miniflow - Complete Workflow Orchestration Engine
# =====================================================

# Core database functionality - Legacy database support for backwards compatibility
from . import database

# Workflow management
from . import workflow_manager

# Scheduler components
from .scheduler import (
    MiniflowInputMonitor,
    MiniflowOutputMonitor,
    WorkflowScheduler,
    create_scheduler,
    create_context_for_task,
    create_context,
    extract_dynamic_values,
    split_variable_path,
    find_node_id,
    get_result_data_for_node
)

# Parallelism engine
from . import parallelism_engine

# Global database manager instance (Singleton Pattern) - DISABLED DUE TO CIRCULAR IMPORTS
_global_db_manager = None

# DATABASE MANAGER FUNCTIONS TEMPORARILY DISABLED
# TODO: Fix circular import issue

# def get_database_manager(db_path: str = "miniflow.db"):
#     """Get global database manager instance (Singleton Pattern)"""
#     # Lazy import to avoid circular imports
#     from .database_manager import DatabaseManager
#     
#     global _global_db_manager
#     if _global_db_manager is None:
#         _global_db_manager = DatabaseManager()
#         _global_db_manager.config.database_path = db_path
#         _global_db_manager.initialize_database()
#     return _global_db_manager

# Backwards compatibility - Legacy functions only for now
def init_database(db_path: str = "miniflow.db"):
    """Legacy init_database function"""
    from .database import init_database as legacy_init_database
    return legacy_init_database(db_path)

def list_workflows(db_path: str = "miniflow.db"):
    """Legacy list_workflows function"""
    from .database import list_workflows as legacy_list_workflows
    result = legacy_list_workflows(db_path)
    return result.data if result.success else []

# Version
__version__ = "1.0.0"

# Single comprehensive __all__ export
__all__ = [
    # Legacy modules
    'database',
    'workflow_manager', 
    'scheduler',
    'parallelism_engine',
    
    # Scheduler components
    'MiniflowInputMonitor',
    'MiniflowOutputMonitor', 
    'WorkflowScheduler',
    'create_scheduler',
    
    # Context management
    'create_context_for_task',
    'create_context',
    'extract_dynamic_values',
    'split_variable_path',
    'find_node_id',
    'get_result_data_for_node',
    
    # New database manager (lazy loaded) - TEMPORARILY DISABLED
    # 'DatabaseManager', 'WorkflowService', 'ExecutionService', 'OrchestrationService',
    
    # Factory functions (temporarily disabled)
    # 'get_database_manager', 'get_workflow_service', 'get_execution_service', 'get_orchestration_service',
    
    # Legacy compatibility
    'init_database',
    'list_workflows',
    
    # Version
    '__version__'
]
