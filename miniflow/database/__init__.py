# Core database functions
from .core import (
    execute_sql_query,
    fetch_one,
    fetch_all,
    check_database_connection,
    create_all_tables,
    create_all_indexes,
    drop_all_tables,
    check_schema,
    get_table_info,
    get_all_table_info,
    init_database
)

# Configuration and exceptions
from .config import DatabaseConfig, DatabaseConnection
from .exceptions import DatabaseError, Result
from .utils import generate_uuid, generate_timestamp, safe_json_dumps, safe_json_loads

# Table-specific functions
from .functions.workflows_table import (
    create_workflow,
    get_workflow,
    delete_workflow,
    list_workflows
)

from .functions.nodes_table import (
    create_node,
    get_node,
    delete_node,
    list_nodes,
    list_workflow_nodes,
    delete_workflow_nodes,
    get_node_dependents,
    get_node_dependencies,
    update_node_params
)

from .functions.edges_table import (
    create_edge,
    get_edge,
    delete_edge,
    list_edges,
    list_workflow_edges,
    delete_workflow_edges
)

from .functions.executions_table import (
    create_execution,
    get_execution,
    delete_execution,
    list_executions,
    set_execution_end_time,
    set_execution_status,
    set_execution_result,
    start_execution,
    stop_execution,
    check_execution_completion
)

from .functions.execution_queue_table import (
    create_task,
    get_task,
    delete_task,
    list_tasks,
    count_tasks,
    list_execution_tasks,
    delete_execution_tasks,
    find_in_queue,
    reorder_execution_queue,
    decrease_dependency_count,
    update_task_status
)

from .functions.execution_results_table import (
    create_record,
    find_record,
    delete_record,
    list_execution_records,
    delete_execution_records,
    combine_execution_records_results,
    get_record_status,
    get_record_timestamp
)

from .functions.triggers_table import (
    create_trigger,
    get_trigger,
    delete_trigger,
    list_workflow_triggers,
    delete_workflow_triggers,
    get_trigger_type,
    list_triggers,
    update_trigger,
    activate_trigger,
    deactivate_trigger
)

# High-level workflow orchestration
from .functions.workflow_orchestration import (
    process_execution_result,
    handle_execution_failure,
    handle_execution_success,
    complete_execution,
    finalize_execution,
    batch_update_dependencies,
    trigger_workflow_execution,
    get_execution_status_summary,
    get_ready_tasks_for_execution,
    mark_task_as_running,
    create_workflow_with_components
)

__all__ = [
    # Core functions
    'execute_sql_query', 'fetch_one', 'fetch_all', 'check_database_connection',
    'create_all_tables', 'create_all_indexes', 'drop_all_tables', 'check_schema',
    'get_table_info', 'get_all_table_info', 'init_database',
    
    # Configuration and exceptions
    'DatabaseConfig', 'DatabaseConnection', 'DatabaseError', 'Result',
    
    # Utilities
    'generate_uuid', 'generate_timestamp', 'safe_json_dumps', 'safe_json_loads',
    
    # Workflow functions
    'create_workflow', 'get_workflow', 'delete_workflow', 'list_workflows',
    
    # Node functions
    'create_node', 'get_node', 'delete_node', 'list_nodes', 'list_workflow_nodes',
    'delete_workflow_nodes', 'get_node_dependents', 'get_node_dependencies',
    'update_node_params',
    
    # Edge functions
    'create_edge', 'get_edge', 'delete_edge', 'list_edges', 'list_workflow_edges',
    'delete_workflow_edges',
    
    # Execution functions
    'create_execution', 'get_execution', 'delete_execution', 'list_executions',
    'set_execution_end_time', 'set_execution_status', 'set_execution_result',
    'start_execution', 'stop_execution', 'check_execution_completion',
    
    # Queue functions
    'create_task', 'get_task', 'delete_task', 'list_tasks', 'count_tasks',
    'list_execution_tasks', 'delete_execution_tasks', 'find_in_queue',
    'reorder_execution_queue', 'decrease_dependency_count',
    'update_task_status',
    
    # Results functions
    'create_record', 'find_record', 'delete_record', 'list_execution_records',
    'delete_execution_records', 'combine_execution_records_results',
    'get_record_status', 'get_record_timestamp',
    
    # Triggers functions
    'create_trigger', 'get_trigger', 'delete_trigger', 'list_workflow_triggers',
    'delete_workflow_triggers', 'get_trigger_type', 'list_triggers', 'update_trigger',
    'activate_trigger', 'deactivate_trigger',
    
    # Orchestration functions
    'process_execution_result', 'handle_execution_failure', 'handle_execution_success',
    'complete_execution', 'finalize_execution', 'batch_update_dependencies',
    'trigger_workflow_execution', 'get_execution_status_summary',
    'get_ready_tasks_for_execution', 'mark_task_as_running', 'create_workflow_with_components'
]
