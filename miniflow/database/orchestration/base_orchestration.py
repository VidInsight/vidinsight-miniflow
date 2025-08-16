# orchestration/base_orchestration.py
import sys
import os

from ..crud import *



class BaseOrchestration:
    """Merkezi CRUD yönetimi ile base orchestration"""
    
    def __init__(self):
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