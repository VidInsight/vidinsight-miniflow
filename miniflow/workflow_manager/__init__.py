"""
Miniflow Workflow Manager Module

Bu modül workflow yönetimi için gerekli bileşenleri içerir:
- WorkflowLoader: JSON workflow dosyalarını database'e yükler
- Trigger: Workflow tetikleme işlemlerini yönetir (gelecek implementasyon)

Kritik Özellik: node_name.variable → node_id.variable dönüşümü
"""

# Workflow loading functionality
from .loader import (
    WorkflowLoader,
    create_workflow_loader,
    load_workflow_from_file,
    load_workflow_from_json_string
)

# Utility functions
from .utils.workflow_parser import (
    parse_workflow_json,
    extract_workflow_metadata,
    validate_workflow_example,
    WorkflowParseError,
    WorkflowValidationError
)

# Trigger functionality
from .trigger import (
    WorkflowTrigger,
    create_workflow_trigger,
    trigger_workflow_manually,
    get_workflow_execution_status,
    get_workflow_ready_tasks
)

__all__ = [
    # Core loader
    'WorkflowLoader',
    'create_workflow_loader',
    'load_workflow_from_file', 
    'load_workflow_from_json_string',
    
    # Parsing utilities
    'parse_workflow_json',
    'extract_workflow_metadata',
    'validate_workflow_example',
    
    # Exceptions
    'WorkflowParseError',
    'WorkflowValidationError',
    
    # Trigger functionality
    'WorkflowTrigger',
    'create_workflow_trigger',
    'trigger_workflow_manually',
    'get_workflow_execution_status',
    'get_workflow_ready_tasks'
]
