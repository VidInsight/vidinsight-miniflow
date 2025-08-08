# services/workflow_service.py - ÖRNEK
from typing import List, Optional
from ..models.workflow import WorkflowCreateRequest, WorkflowCreateResponse, WorkflowGetResponse
from ...exceptions import ValidationError, BusinessLogicError

class WorkflowService:
    """Workflow business logic katmanı"""
    
    def __init__(self, miniflow_core):
        self.core = miniflow_core
    
    async def create_workflow(self, workflow_data: WorkflowCreateRequest) -> WorkflowCreateResponse:
        """Workflow oluşturma business logic'i"""
        
        # 1. Validation
        await self._validate_workflow_data(workflow_data)
        
        # 2. Business Rules
        await self._check_workflow_name_unique(workflow_data.name)
        await self._validate_workflow_structure(workflow_data.nodes, workflow_data.edges)
        
        # 3. Core işlemi
        workflow_dict = workflow_data.model_dump()
        result = self.core.workflow_create(workflow_dict)
        
        # 4. Response mapping
        return WorkflowCreateResponse(
            workflow_id=result["workflow_id"],
            created_at=result["created_at"],
            nodes=result["nodes"],
            edges=result["edges"],
            triggers=result["triggers"]
        )
    
    async def get_workflow(self, workflow_id: str) -> WorkflowGetResponse:
        """Workflow detay getirme"""
        
        # 1. Validation
        if not workflow_id:
            raise ValidationError("Workflow ID required")
        
        # 2. Core işlemi
        workflow = self.core.workflow_get(workflow_id)
        
        # 3. Business logic (örn: permission check)
        await self._check_workflow_access(workflow)
        
        # 4. Response mapping
        return WorkflowGetResponse(
            workflow_id=workflow["id"],
            name=workflow["name"],
            description=workflow.get("description"),
            status=workflow["status"],
            priority=workflow["priority"],
            created_at=workflow["created_at"],
            updated_at=workflow["updated_at"],
            nodes=workflow.get("nodes", []),
            edges=workflow.get("edges", []),
            triggers=workflow.get("triggers", [])
        )
    
    async def list_workflows(self, include_detail: bool = False) -> List[WorkflowGetResponse]:
        """Workflow listesi getirme"""
        
        # 1. Business logic (örn: filtering, pagination)
        workflows = self.core.workflow_list(include_detail=include_detail)
        
        # 2. Response mapping
        workflow_responses = []
        for wf in workflows:
            workflow_responses.append(WorkflowGetResponse(
                workflow_id=wf["id"],
                name=wf["name"],
                description=wf.get("description"),
                status=wf["status"],
                priority=wf["priority"],
                created_at=wf["created_at"],
                updated_at=wf["updated_at"],
                nodes=wf.get("nodes", []),
                edges=wf.get("edges", []),
                triggers=wf.get("triggers", [])
            ))
        
        return workflow_responses
    
    # Private methods - Business logic
    async def _validate_workflow_data(self, workflow_data: WorkflowCreateRequest):
        """Workflow data validation"""
        if not workflow_data.name.strip():
            raise ValidationError("Workflow name cannot be empty")
        
        if len(workflow_data.name) > 100:
            raise ValidationError("Workflow name too long")
    
    async def _check_workflow_name_unique(self, name: str):
        """Workflow name uniqueness check"""
        # Database'de aynı isimde workflow var mı kontrol et
        existing_workflows = self.core.workflow_list()
        for wf in existing_workflows:
            if wf["name"] == name:
                raise BusinessLogicError(f"Workflow with name '{name}' already exists")
    
    async def _validate_workflow_structure(self, nodes: List, edges: List):
        """Workflow structure validation"""
        if not nodes:
            raise ValidationError("Workflow must have at least one node")
        
        # Node connectivity check
        node_ids = {node.get("name") for node in nodes}
        for edge in edges:
            if edge.get("source") not in node_ids or edge.get("target") not in node_ids:
                raise ValidationError("Edge references non-existent node")
    
    async def _check_workflow_access(self, workflow: dict):
        """Workflow access permission check"""
        # Future: User permission logic
        pass
