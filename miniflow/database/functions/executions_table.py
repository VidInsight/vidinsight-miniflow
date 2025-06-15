from ..core import execute_sql_query, fetch_all, fetch_one, handle_db_errors
from ..utils import generate_uuid, safe_json_dumps, generate_timestamp
from ..exceptions import Result


# Temel CRUD operasyonaları
@handle_db_errors("create execution")
def create_execution(db_path, workflow_id):
    execution_id = generate_uuid()
    timestamp = generate_timestamp()

    query = """
        INSERT INTO executions (id, workflow_id, status, started_at, ended_at, results)
        VALUES (?, ?, 'pending', ?, ?, '{}')
        """
    result = execute_sql_query(
        db_path=db_path, 
        query=query, 
        params=(execution_id, workflow_id, timestamp, timestamp))
    
    if not result.success:
        return Result.error(f"Failed to create execution: {result.error}")
    return Result.success({"execution_id": execution_id})

@handle_db_errors("get execution")
def get_execution(db_path, execution_id):
    query = "SELECT * FROM executions WHERE id = ?"
    result = fetch_one(db_path=db_path, query=query, params=(execution_id,))

    if not result.success:
        return Result.error(f"Failed to get execution: {result.error}")
    return Result.success(result.data)

@handle_db_errors("delete executions")
def delete_execution(db_path, execution_id):
    query = "DELETE FROM executions WHERE id = ?"
    result = execute_sql_query(
        db_path=db_path, 
        query=query, 
        params=(execution_id,))
        
    if not result.success:
        return Result.error(f"Failed to delete execution: {result.error}")
    return Result.success({"deleted": True, "execution_id": execution_id})

@handle_db_errors("list executions")
def list_executions(db_path, workflow_id=None, status=None, limit=100, offset=0):
    query = "SELECT * FROM executions"
    params = []
    conditions = []
    if workflow_id:
        conditions.append("workflow_id = ?")
        params.append(workflow_id)
    if status:
        conditions.append("status = ?")
        params.append(status)
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY started_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    result = fetch_all(db_path=db_path, query=query, params=params)
    if not result.success:
        return Result.error(f"Failed to list executions: {result.error}")
    return Result.success(result.data)

# Scheduler için gerekli fonksyonlar
@handle_db_errors("set execution ended_at")
def set_execution_end_time(db_path, execution_id, ended_at):
    query = """
    UPDATE executions 
    SET ended_at = ? 
    WHERE id = ?
    """
    result = execute_sql_query(
        db_path=db_path,
        query=query, 
        params=(ended_at, execution_id))

    if not result.success:
        return Result.error(f"Failed to update execution results: {result.error}")
    return Result.success({"updated": True})

@handle_db_errors("set execution status")
def set_execution_status(db_path, execution_id, status_update):
    timestamp = generate_timestamp()
    if status_update == 'running':
        query = """
        UPDATE executions 
        SET status = ?, started_at = ? 
        WHERE id = ?
        """
        params = (status_update, timestamp, execution_id)
    elif status_update in ['completed', 'failed', 'cancelled']:
        query = """
        UPDATE executions 
        SET status = ?, ended_at = ? 
        WHERE id = ?
        """
        params = (status_update, timestamp, execution_id)

    result = execute_sql_query(
        db_path=db_path, 
        query=query,
        params=params)
    
    if not result.success:
        return Result.error(f"Failed to update execution status: {result.error}")
    return Result.success({"updated": True})

@handle_db_errors("set execution result")
def set_execution_result(db_path, execution_id, execution_result):
    query = """
    UPDATE executions 
    SET results = ? 
    WHERE id = ?
    """
    result = execute_sql_query(
        db_path=db_path,
        query=query, 
        params=(safe_json_dumps(execution_result), execution_id))

    if not result.success:
        return Result.error(f"Failed to update execution results: {result.error}")
    return Result.success({"updated": True})

@handle_db_errors("start execution")
def start_execution(db_path, workflow_id):
    """Starts a workflow execution by creating execution record and queueing tasks"""
    from ..functions.nodes_table import list_workflow_nodes, get_node_dependencies
    from ..functions.execution_queue_table import create_task
    from ..functions.edges_table import list_workflow_edges
    
    # Step 1: Create execution record
    execution_result = create_execution(db_path, workflow_id)
    if not execution_result.success:
        return execution_result
    
    execution_id = execution_result.data["execution_id"]
    
    # Step 2: Get all workflow nodes
    nodes_result = list_workflow_nodes(db_path, workflow_id)
    if not nodes_result.success:
        return Result.error(f"Failed to get workflow nodes: {nodes_result.error}")
    
    # Step 3: Calculate dependency counts for each node
    dependency_counts = {}
    edges_result = list_workflow_edges(db_path, workflow_id)
    if not edges_result.success:
        return Result.error(f"Failed to get workflow edges: {edges_result.error}")
    
    # Initialize all nodes with 0 dependencies
    for node in nodes_result.data:
        dependency_counts[node["id"]] = 0
    
    # Count incoming edges for each node
    for edge in edges_result.data:
        to_node_id = edge["to_node_id"]
        if to_node_id in dependency_counts:
            dependency_counts[to_node_id] += 1
    
    # Step 4: Create tasks in execution queue
    created_tasks = []
    for node in nodes_result.data:
        node_id = node["id"]
        dependency_count = dependency_counts.get(node_id, 0)
        
        task_result = create_task(
            db_path=db_path,
            execution_id=execution_id,
            node_id=node_id,
            dependency_count=dependency_count,
            priority=0  # Default priority, can be enhanced later
        )
        
        if not task_result.success:
            return Result.error(f"Failed to create task for node {node_id}: {task_result.error}")
        
        created_tasks.append({
            "task_id": task_result.data["queue_id"],
            "node_id": node_id,
            "dependency_count": dependency_count
        })
    
    # Step 5: Update execution status to running
    status_result = set_execution_status(db_path, execution_id, 'running')
    if not status_result.success:
        return Result.error(f"Failed to update execution status: {status_result.error}")
    
    return Result.success({
        "execution_id": execution_id,
        "workflow_id": workflow_id,
        "created_tasks": created_tasks,
        "task_count": len(created_tasks),
        "ready_tasks": len([t for t in created_tasks if t["dependency_count"] == 0])
    })

@handle_db_errors("stop execution")
def stop_execution(db_path, execution_id):
    """Stops a running execution by cancelling pending tasks"""
    from ..functions.execution_queue_table import delete_execution_tasks
    
    # Step 1: Cancel all pending tasks
    cancel_result = delete_execution_tasks(db_path, execution_id)
    if not cancel_result.success:
        return cancel_result
    
    # Step 2: Update execution status to cancelled
    status_result = set_execution_status(db_path, execution_id, 'cancelled')
    if not status_result.success:
        return Result.error(f"Failed to update execution status: {status_result.error}")
    
    return Result.success({
        "execution_id": execution_id,
        "status": "cancelled",
        "cancelled_tasks": cancel_result.data.get("cancelled_tasks", 0),
        "deleted_tasks": cancel_result.data.get("deleted_tasks", 0)
    })

@handle_db_errors("check execution completion")
def check_execution_completion(db_path, execution_id):
    """Checks if execution is complete by examining remaining tasks"""
    from ..functions.execution_queue_table import list_execution_tasks
    
    # Get all tasks for this execution
    tasks_result = list_execution_tasks(db_path, execution_id)
    if not tasks_result.success:
        return tasks_result
    
    # Count tasks by status
    status_counts = {}
    for task in tasks_result.data:
        status = task["status"]
        status_counts[status] = status_counts.get(status, 0) + 1
    
    # Check if execution is complete
    pending_count = status_counts.get('pending', 0)
    ready_count = status_counts.get('ready', 0)
    running_count = status_counts.get('running', 0)
    
    is_complete = (pending_count + ready_count + running_count) == 0
    
    return Result.success({
        "execution_id": execution_id,
        "is_complete": is_complete,
        "status_counts": status_counts,
        "total_tasks": len(tasks_result.data)
    })

