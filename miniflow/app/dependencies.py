"""
FastAPI Dependencies - Dependency injection için kullanılacak fonksiyonlar
"""

from miniflow.app.services import WorkflowService, NodeService, EdgeService, ScriptService, ExecutionService, EnvVarService
from miniflow.main import MiniflowCore

# Global core instance - main.py tarafından set edilecek
_core_instance = None

def set_core_instance(core: MiniflowCore) -> None:
    """External core instance'ı set et (main.py tarafından kullanılır)"""
    global _core_instance
    _core_instance = core

def get_core() -> MiniflowCore:
    """MiniflowCore instance'ını getir"""
    global _core_instance
    if _core_instance is None:
        # Fallback: Eğer main.py tarafından set edilmemişse default oluştur
        # Bu durumda sadece API çalışır, scheduler kapalı olur
        _core_instance = MiniflowCore(db_type="sqlite", db_name="miniflow_dev", enable_scheduler=False)
        _core_instance.start()
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
