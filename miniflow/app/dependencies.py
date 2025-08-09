"""
FastAPI Dependencies - Dependency injection için kullanılacak fonksiyonlar
"""

from miniflow.app.services import WorkflowService, NodeService, EdgeService, ScriptService, ExecutionService, EnvVarService
from miniflow.main import MiniflowCore

# Global core instance (gerçek uygulamada configuration'dan gelecek)
_core_instance = None

def get_core() -> MiniflowCore:
    """MiniflowCore instance'ını getir"""
    global _core_instance
    if _core_instance is None:
        # TODO: Gerçek configuration ile initialize et
        # For now, use SQLite as default for development
        _core_instance = MiniflowCore(db_type="sqlite", db_name="miniflow_dev.db", enable_scheduler=False)
    return _core_instance

def get_workflow_service() -> WorkflowService:
    """WorkflowService instance'ını getir"""
    core = get_core()
    return WorkflowService(core)

def get_node_service() -> NodeService:
    """NodeService instance'ını getir"""
    core = get_core()
    return NodeService(core)

def get_edge_service() -> EdgeService:
    """EdgeService instance'ını getir"""
    core = get_core()
    return EdgeService(core)

def get_script_service() -> ScriptService:
    """ScriptService instance'ını getir"""
    core = get_core()
    return ScriptService(core)

def get_execution_service() -> ExecutionService:
    """ExecutionService instance'ını getir"""
    core = get_core()
    return ExecutionService(core)

def get_env_var_service() -> EnvVarService:
    """EnvVarService instance'ını getir"""
    core = get_core()
    return EnvVarService(core)
