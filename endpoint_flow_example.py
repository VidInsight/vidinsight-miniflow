# YENİ YAPI - Endpoint → Service → Core Akışı

# 1. ENDPOINT (HTTP Handling)
# routes/v1/workflow.py
@router.post("/workflows", response_model=WorkflowCreateResponse)
async def create_workflow(
    request: WorkflowCreateRequest,
    service: WorkflowService = Depends(get_workflow_service)  # Service injection
):
    """Endpoint sadece HTTP handling yapar"""
    # Request'i service'e gönder
    return await service.create_workflow(request)

# 2. SERVICE (Business Logic)
# services/workflow_service.py
class WorkflowService:
    def __init__(self, miniflow_core: MiniflowCore):
        self.core = miniflow_core
        self.validator = WorkflowValidator()  # Validator injection
    
    async def create_workflow(self, request: WorkflowCreateRequest) -> WorkflowCreateResponse:
        """Business logic burada"""
        
        # 1. VALIDATION
        self.validator.validate_workflow_name(request.name)
        self.validator.validate_workflow_structure(request.nodes, request.edges)
        
        # 2. BUSINESS RULES
        await self._check_workflow_name_unique(request.name)
        await self._validate_workflow_permissions(request)
        
        # 3. CORE İŞLEMİ
        workflow_dict = request.model_dump()
        result = self.core.workflow_create(workflow_dict)  # Core'a erişim
        
        # 4. RESPONSE MAPPING
        return WorkflowCreateResponse(
            workflow_id=result["workflow_id"],
            created_at=result["created_at"],
            nodes=result["nodes"],
            edges=result["edges"],
            triggers=result["triggers"]
        )
    
    async def get_workflow(self, workflow_id: str) -> WorkflowGetResponse:
        """Workflow get business logic"""
        
        # 1. VALIDATION
        if not workflow_id:
            raise ValidationError("Workflow ID required")
        
        # 2. CORE İŞLEMİ
        workflow = self.core.workflow_get(workflow_id)
        
        # 3. BUSINESS LOGIC
        await self._check_workflow_access(workflow)
        
        # 4. RESPONSE MAPPING
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

# 3. VALIDATOR (Validation Logic)
# validators/workflow_validator.py
class WorkflowValidator:
    @staticmethod
    def validate_workflow_name(name: str) -> bool:
        """Workflow name validation"""
        if not name or not name.strip():
            raise ValidationError("Workflow name cannot be empty")
        
        if len(name) > 100:
            raise ValidationError("Workflow name too long")
        
        return True
    
    @staticmethod
    def validate_workflow_structure(nodes: List[Dict], edges: List[Dict]) -> bool:
        """Complex workflow structure validation"""
        if not nodes:
            raise ValidationError("Workflow must have at least one node")
        
        # Node validation
        node_names = set()
        for node in nodes:
            if not node.get("name"):
                raise ValidationError("All nodes must have a name")
            
            if node["name"] in node_names:
                raise ValidationError(f"Duplicate node name: {node['name']}")
            
            node_names.add(node["name"])
        
        # Edge validation
        for edge in edges:
            source = edge.get("source")
            target = edge.get("target")
            
            if not source or not target:
                raise ValidationError("All edges must have source and target")
            
            if source not in node_names:
                raise ValidationError(f"Edge source '{source}' not found")
            
            if target not in node_names:
                raise ValidationError(f"Edge target '{target}' not found")
        
        return True

# 4. DEPENDENCY INJECTION
# routes/dependencies.py
def get_workflow_service(
    core: MiniflowCore = Depends(get_miniflow_core)
) -> WorkflowService:
    """Service instance'ı oluştur"""
    return WorkflowService(core)

# 5. COMPLETE FLOW EXAMPLE
"""
HTTP Request → Endpoint → Service → Validator → Core → Response

1. Client POST /api/v1/workflows
2. Endpoint: HTTP handling + service injection
3. Service: Business logic + validation + core call
4. Validator: Complex validation rules
5. Core: Database operations
6. Service: Response mapping
7. Endpoint: HTTP response
8. Client: Gets response
"""

# ÖRNEK: Script endpoint'i de aynı pattern'i kullanır
@router.post("/scripts", response_model=ScriptCreateResponse)
async def create_script(
    request: ScriptCreateRequest,
    service: ScriptService = Depends(get_script_service)
):
    """Script oluşturma endpoint'i"""
    return await service.create_script(request)

class ScriptService:
    def __init__(self, miniflow_core: MiniflowCore):
        self.core = miniflow_core
        self.validator = ScriptValidator()
    
    async def create_script(self, request: ScriptCreateRequest) -> ScriptCreateResponse:
        """Script oluşturma business logic"""
        
        # 1. VALIDATION
        self.validator.validate_script_name(request.name)
        self.validator.validate_script_content(request.file_content)
        self.validator.validate_script_parameters(request.input_params, request.output_params)
        
        # 2. BUSINESS RULES
        await self._check_script_name_unique(request.name)
        
        # 3. CORE İŞLEMİ
        script_data = {
            'name': request.name,
            'description': request.description,
            'input_params': request.input_params,
            'output_params': request.output_params
        }
        
        result = self.core.script_create(
            script_data=script_data,
            script_content=request.file_content
        )
        
        # 4. RESPONSE MAPPING
        return ScriptCreateResponse(
            script_id=result['script_id'],
            absolute_path=result['absolute_path'],
            created_at=result['created_at']
        )
