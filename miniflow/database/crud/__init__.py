"""
DATABASE CRUD MODULE
===================

Bu modül Miniflow sisteminin tüm database CRUD (Create, Read, Update, Delete) 
operasyonları için specialized sınıfları sağlar. Her entity için optimize edilmiş
CRUD sınıfları, complex query'ler ve business logic encapsulation sağlar.

MODÜL SORUMLULUKLARI:
====================
1. Entity-Specific CRUD Operations - Her model için özelleştirilmiş işlemler
2. Complex Query Implementation - Join'li ve aggregate query'ler
3. Business Logic Encapsulation - Domain-specific validation ve processing
4. Performance Optimization - Bulk operations ve efficient queries
5. Transaction Management - Multi-table operation coordination

CRUD ARCHITECTURE:
==================
┌─────────────────┐
│   BaseCRUD      │ ← Generic CRUD operations (T: Model type)
│                 │
│ • create()      │
│ • find_by_id()  │
│ • update()      │
│ • delete()      │
│ • bulk_ops()    │
└─────────────────┘
         ▲
         │ (inherits)
         │
    ┌─────────────────────────────────────────────────────┐
    │                                                     │
    │  Entity-Specific CRUD Classes                      │
    │                                                     │
    ├─ WorkflowCRUD    ├─ ExecutionCRUD                  │
    ├─ NodeCRUD        ├─ ExecutionInputCRUD             │
    ├─ EdgeCRUD        ├─ ExecutionOutputCRUD            │
    ├─ ScriptCRUD      ├─ ArchivedExecutionCRUD          │
    ├─ TriggerCRUD     └─ AuditLogCRUD                   │
    └─────────────────────────────────────────────────────┘

CRUD KATEGORILERI:
==================

**CORE WORKFLOW ENTITIES:**
• WorkflowCRUD: Workflow tanım ve lifecycle management
• NodeCRUD: Node definition ve relationship management  
• EdgeCRUD: Workflow connection ve dependency management
• ScriptCRUD: Reusable script component management
• TriggerCRUD: Workflow activation rule management

**EXECUTION RUNTIME ENTITIES:**
• ExecutionCRUD: Workflow execution lifecycle ve progress tracking
• ExecutionInputCRUD: Task queue management ve ready task optimization
• ExecutionOutputCRUD: Result collection ve dynamic parameter resolution
• ArchivedExecutionCRUD: Historical data management ve cleanup

**SYSTEM MONITORING:**
• AuditLogCRUD: System change tracking ve compliance logging

USAGE PATTERNS:
==============
```python
# Pattern 1: Basic CRUD Operations
workflow_crud = WorkflowCRUD()
with session_context() as session:
    workflow = workflow_crud.create(session, name="test", status="active")
    workflow = workflow_crud.find_by_id(session, workflow_id)
    workflow_crud.update(session, workflow_id, status="inactive")
    workflow_crud.delete(session, workflow_id)

# Pattern 2: Complex Query Operations  
execution_crud = ExecutionCRUD()
with session_context() as session:
    # Business-specific methods
    active_executions = execution_crud.get_active_executions(session)
    execution_crud.increment_executed_nodes(session, execution_id)
    
# Pattern 3: Performance-Optimized Operations
input_crud = ExecutionInputCRUD()
with session_context() as session:
    # Scheduler-optimized queries
    ready_tasks = input_crud.get_ready_tasks_with_details(session, limit=100)
    removed_count = input_crud.bulk_delete_by_ids(session, task_ids)
```

PERFORMANCE FEATURES:
====================
• Bulk Operations: Multiple record insert/update/delete
• Optimized Queries: Index-aware query design  
• Lazy Loading: Relationship loading optimization
• Batch Processing: Large dataset handling
• Connection Pooling: Efficient connection reuse
"""

# =============================================================================
# CORE WORKFLOW ENTITIES
# Workflow definition ve structure management CRUD'ları
# =============================================================================
from .workflow_crud import WorkflowCRUD        # Workflow lifecycle management
from .node_crud import NodeCRUD                # Node definition management
from .edge_crud import EdgeCRUD                # Workflow connection management
from .script_crud import ScriptCRUD            # Reusable script management
from .trigger_crud import TriggerCRUD          # Workflow activation rules

# =============================================================================
# EXECUTION RUNTIME ENTITIES  
# Workflow execution ve task management CRUD'ları
# =============================================================================
from .execution_crud import ExecutionCRUD                      # Execution lifecycle
from .execution_input_crud import ExecutionInputCRUD          # Task queue management
from .execution_output_crud import ExecutionOutputCRUD        # Result management
from .archived_execution_crud import ArchivedExecutionCRUD    # Historical data

# =============================================================================
# SYSTEM MONITORING
# System audit ve logging CRUD'ları
# =============================================================================
from .audit_log_crud import AuditLogCRUD      # System change tracking

# =============================================================================
# PUBLIC API EXPORTS
# Bu modülden dışarıya açılan tüm CRUD sınıfları
# =============================================================================
__all__ = [
    # Core Workflow CRUD Classes
    "WorkflowCRUD",        # Workflow definition management
    "NodeCRUD",            # Node component management
    "EdgeCRUD",            # Workflow connection management
    "ScriptCRUD",          # Script component management
    "TriggerCRUD",         # Activation rule management
    
    # Execution Runtime CRUD Classes
    "ExecutionCRUD",       # Execution lifecycle management
    "ExecutionInputCRUD",  # Task queue and scheduling
    "ExecutionOutputCRUD", # Result collection and processing
    "ArchivedExecutionCRUD", # Historical execution data
    
    # System Monitoring CRUD Classes
    "AuditLogCRUD"         # System audit and change tracking
]