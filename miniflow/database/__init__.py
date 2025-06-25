# database/__init__.py

#25.06.2025 03.21

from .core import (
    init_database,
    drop_all_tables,
    check_database_connection,
    get_table_info,
    get_all_table_info,
)

from .config import DatabaseConfig, DatabaseConnection
from .schema import Base
from .utils import safe_json_dumps, safe_json_loads

# Workflows
from .functions.workflows_table import (
    create_workflow, get_workflow, list_workflows, delete_workflow
)

# Nodes
from .functions.nodes_table import (
    create_node, get_node, list_nodes, list_workflow_nodes, delete_node,
    delete_workflow_nodes, get_node_dependencies, get_node_dependents, update_node_params
)

# Edges
from .functions.edges_table import (
    create_edge, get_edge, delete_edge, list_edges, list_workflow_edges, delete_workflow_edges
)

# Execution Queue
from .functions.execution_queue_table import (
    create_task, get_task, delete_task, list_tasks, count_tasks, list_execution_tasks,
    delete_execution_tasks, find_in_queue, reorder_execution_queue, decrease_dependency_count,
    update_task_status
)

# Execution Results
from .functions.execution_results_table import (
    create_record, find_record, delete_record, list_execution_records,
    delete_execution_records, combine_execution_records_results,
    get_record_status, get_record_timestamp
)

# Executions
from .functions.executions_table import (
    create_execution, get_execution, delete_execution, list_executions,
    set_execution_end_time, set_execution_status, set_execution_result,
    start_execution, stop_execution, check_execution_completion
)

# Triggers
from .functions.triggers_table import (
    create_trigger, get_trigger, delete_trigger, list_triggers,
    list_workflow_triggers, delete_workflow_triggers, get_trigger_type,
    update_trigger, activate_trigger, deactivate_trigger
)

# Workflow Orchestration
from .functions.workflow_orchestration import (
    get_ready_tasks_for_execution, mark_task_as_running, process_execution_result,
    handle_execution_success, handle_execution_failure, complete_execution,
    finalize_execution, batch_update_dependencies, trigger_workflow_execution,
    get_execution_status_summary, create_workflow_with_components
)

__all__ = [
    # Temel bileşenler
    "init_database", "drop_all_tables", "check_database_connection",
    "get_table_info", "get_all_table_info",
    "DatabaseConfig", "DatabaseConnection", "Base",
    "safe_json_dumps", "safe_json_loads",

    # Workflows
    "create_workflow", "get_workflow", "list_workflows", "delete_workflow",

    # Nodes
    "create_node", "get_node", "list_nodes", "list_workflow_nodes", "delete_node",
    "delete_workflow_nodes", "get_node_dependencies", "get_node_dependents", "update_node_params",

    # Edges
    "create_edge", "get_edge", "delete_edge", "list_edges", "list_workflow_edges", "delete_workflow_edges",

    # Execution Queue
    "create_task", "get_task", "delete_task", "list_tasks", "count_tasks", "list_execution_tasks",
    "delete_execution_tasks", "find_in_queue", "reorder_execution_queue", "decrease_dependency_count",
    "update_task_status",

    # Execution Results
    "create_record", "find_record", "delete_record", "list_execution_records",
    "delete_execution_records", "combine_execution_records_results",
    "get_record_status", "get_record_timestamp",

    # Executions
    "create_execution", "get_execution", "delete_execution", "list_executions",
    "set_execution_end_time", "set_execution_status", "set_execution_result",
    "start_execution", "stop_execution", "check_execution_completion",

    # Triggers
    "create_trigger", "get_trigger", "delete_trigger", "list_triggers",
    "list_workflow_triggers", "delete_workflow_triggers", "get_trigger_type",
    "update_trigger", "activate_trigger", "deactivate_trigger",

    # Orchestration
    "get_ready_tasks_for_execution", "mark_task_as_running", "process_execution_result",
    "handle_execution_success", "handle_execution_failure", "complete_execution",
    "finalize_execution", "batch_update_dependencies", "trigger_workflow_execution",
    "get_execution_status_summary", "create_workflow_with_components",
]
