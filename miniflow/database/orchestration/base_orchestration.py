from ..crud import (
    WorkflowCRUD,
    NodeCRUD,
    EdgeCRUD,
    EnvarCRUD,
    ScriptCRUD,
    ExecutionCRUD,
    ExecutionInputCRUD,
    ExecutionOutputCRUD,
    ArchivedExecutionCRUD,
    AuditLogCRUD
)


class BaseOrchestration:
    """
    Base orchestration class providing centralized CRUD management for all orchestrators.
    
    This class serves as the foundation for all orchestration operations by providing
    access to all CRUD operations in a centralized manner. It eliminates code duplication
    and ensures consistent database access patterns across all orchestrators.
    """
    
    def __init__(self):
        """
        Initialize BaseOrchestration with all CRUD instances.
        
        Creates instances of all CRUD classes for workflow management, execution tracking,
        and audit logging. This centralized approach ensures all orchestrators have
        consistent access to database operations.
        """
        # Core CRUDs
        self.workflow_crud = WorkflowCRUD()
        self.node_crud = NodeCRUD()
        self.edge_crud = EdgeCRUD()
        self.script_crud = ScriptCRUD()
        self.envar_crud = EnvarCRUD()
        
        # Execution CRUDs
        self.execution_crud = ExecutionCRUD()
        self.execution_input_crud = ExecutionInputCRUD()
        self.execution_output_crud = ExecutionOutputCRUD()
        self.archived_execution_crud = ArchivedExecutionCRUD()
        
        # Audit CRUDs
        self.audit_log_crud = AuditLogCRUD()