from ..core import execute_sql_query, fetch_all, fetch_one, handle_db_errors
from ..utils import generate_uuid, safe_json_dumps, generate_timestamp
from ..exceptions import Result


# Temel CRUD operasyonaları
@handle_db_errors("create task")
def create_task(db_path, execution_id, node_id, dependency_count, priority=0):
    task_id = generate_uuid()
    initial_status = 'ready' if dependency_count == 0 else 'pending'

    query = """
    INSERT INTO execution_queue 
    (id, execution_id, node_id, status, priority, dependency_count)
    VALUES (?, ?, ?, ?, ?, ?)
    """
    result = execute_sql_query(
        db_path=db_path, 
        query=query, 
        params=(task_id, execution_id, node_id, initial_status, priority, dependency_count))

    if not result.success:
        return Result.error(f"Failed to add to execution queue: {result.error}")
    return Result.success({"queue_id": task_id})

@handle_db_errors("get task")
def get_task(db_path, task_id):
    query = "SELECT * FROM execution_queue WHERE id = ?"
    result = fetch_one(db_path=db_path, query=query, params=(task_id,))

    if not result.success:
        return Result.error(f"Failed to get task: {result.error}")
    return Result.success(result.data)

@handle_db_errors("delete task")
def delete_task(db_path, task_id):
    query = "DELETE FROM execution_queue WHERE id = ?"
    result = execute_sql_query(
        db_path=db_path, 
        query=query, 
        params=(task_id,))
    
    if not result.success:
        return Result.error(f"Failed to remove from execution queue: {result.error}")
    return Result.success({"removed": True})

@handle_db_errors("list tasks")
def list_tasks(db_path, status=None):
    query = """
    SELECT eq.*, n.name as node_name, n.type as node_type
    FROM execution_queue eq
    JOIN nodes n ON eq.node_id = n.id
    """
    params = []
    if status:
        query += " AND eq.status = ?"
        params.append(status)
    
    query += " ORDER BY eq.priority DESC, eq.dependency_count ASC"
    result = fetch_all(db_path=db_path, query=query, params=params)
    
    if not result.success:
        return Result.error(f"Failed to list taks: {result.error}")
    return Result.success([dict(row) for row in result.data])

@handle_db_errors("count tasks")
def count_tasks(db_path, status=None):
    query = "SELECT COUNT(*) as count FROM execution_queue WHERE execution_id = ?"
    params = []
    if status:
        query += " AND status = ?"
        params.append(status)

    result = fetch_one(db_path=db_path, query=query, params=params)
    if not result.success:
        return Result.error(f"Failed to count tasks: {result.error}")
    return Result.success(result.data['count'] if result.data else 0)

# Executions tablosu ile bağlantılı işlemler
@handle_db_errors("list execution tasks")
def list_execution_tasks(db_path, execution_id, status=None):
    query = """
    SELECT eq.*, n.name as node_name, n.type as node_type, n.script, n.params
    FROM execution_queue eq
    JOIN nodes n ON eq.node_id = n.id
    WHERE eq.execution_id = ?
    """
    params = [execution_id]
    
    if status:
        query += " AND eq.status = ?"
        params.append(status)
    
    query += " ORDER BY eq.priority DESC, eq.dependency_count ASC"
    result = fetch_all(db_path=db_path, query=query, params=params)
    
    if not result.success:
        return Result.error(f"Failed to list execution tasks: {result.error}")
    return Result.success(result.data)

@handle_db_errors("delete execution tasks")
def delete_execution_tasks(db_path, execution_id):
    # First, update status to cancelled for tracking
    update_query = """
    UPDATE execution_queue 
    SET status = 'cancelled' 
    WHERE execution_id = ? AND status NOT IN ('completed', 'running')
    """
    update_result = execute_sql_query(db_path=db_path, query=update_query, params=(execution_id,))
    
    if not update_result.success:
        return Result.error(f"Failed to cancel execution tasks: {update_result.error}")
    
    # Then delete the cancelled tasks
    delete_query = "DELETE FROM execution_queue WHERE execution_id = ? AND status = 'cancelled'"
    delete_result = execute_sql_query(db_path=db_path, query=delete_query, params=(execution_id,))
    
    if not delete_result.success:
        return Result.error(f"Failed to delete execution tasks: {delete_result.error}")
    
    return Result.success({
        "cancelled": True, 
        "execution_id": execution_id,
        "cancelled_tasks": update_result.data.get("affected_rows", 0),
        "deleted_tasks": delete_result.data.get("affected_rows", 0)
    })

@handle_db_errors("find in queue")
def find_in_queue(db_path, execution_id, node_id):
    query = """
    SELECT * FROM execution_queue 
    WHERE execution_id = ? AND node_id = ?
    """
    
    result = fetch_one(db_path=db_path, query=query, params=(execution_id, node_id))
    if not result.success:
        return Result.error(f"Failed to find in execution queue: {result.error}")
    return Result.success(dict(result.data) if result.data else None)

# Scheduler için gerekli fonksiyonlar
@handle_db_errors("reorder execution queue")
def reorder_execution_queue(db_path):
    # Step 1: Update tasks with dependency_count = 0 to 'ready' status
    update_query = """
    UPDATE execution_queue 
    SET status = 'ready' 
    WHERE dependency_count = 0 AND status = 'pending'
    """
    update_result = execute_sql_query(db_path=db_path, query=update_query, params=())
    
    if not update_result.success:
        return Result.error(f"Failed to update ready tasks: {update_result.error}")
    
    # Step 2: Get reordered ready tasks
    select_query = """
    SELECT eq.*, n.name as node_name, n.type as node_type
    FROM execution_queue eq
    JOIN nodes n ON eq.node_id = n.id
    WHERE eq.status = 'ready'
    ORDER BY eq.priority DESC, eq.dependency_count ASC
    """
    select_result = fetch_all(db_path=db_path, query=select_query, params=())
    
    if not select_result.success:
        return Result.error(f"Failed to get reordered tasks: {select_result.error}")
    
    return Result.success({
        "ready_tasks_updated": update_result.data.get("affected_rows", 0),
        "ready_tasks": select_result.data,
        "ready_count": len(select_result.data)
    })

@handle_db_errors("decrease dependency count")
def decrease_dependency_count(db_path, task_id):
    # Get current dependency count
    get_query = "SELECT dependency_count, status FROM execution_queue WHERE id = ?"
    get_result = fetch_one(db_path=db_path, query=get_query, params=(task_id,))
    
    if not get_result.success:
        return Result.error(f"Failed to get task dependency count: {get_result.error}")
    
    if not get_result.data:
        return Result.error(f"Task not found: {task_id}")
    
    current_count = get_result.data["dependency_count"]
    current_status = get_result.data["status"]
    
    # Calculate new dependency count
    new_count = max(0, current_count - 1)
    
    # Determine new status
    new_status = current_status
    if new_count == 0 and current_status == 'pending':
        new_status = 'ready'
    
    # Update the task
    update_query = """
    UPDATE execution_queue 
    SET dependency_count = ?, status = ?
    WHERE id = ?
    """
    update_result = execute_sql_query(
        db_path=db_path, 
        query=update_query, 
        params=(new_count, new_status, task_id)
    )
    
    if not update_result.success:
        return Result.error(f"Failed to update task dependency count: {update_result.error}")
    
    return Result.success({
        "updated": True,
        "task_id": task_id,
        "old_dependency_count": current_count,
        "new_dependency_count": new_count,
        "old_status": current_status,
        "new_status": new_status,
        "became_ready": (new_status == 'ready' and current_status != 'ready')
    })

@handle_db_errors("update task status")
def update_task_status(db_path, task_id, new_status):
    """Updates the status of a specific task"""
    query = "UPDATE execution_queue SET status = ? WHERE id = ?"
    result = execute_sql_query(db_path=db_path, query=query, params=(new_status, task_id))
    
    if not result.success:
        return Result.error(f"Failed to update task status: {result.error}")
    
    return Result.success({
        "updated": True,
        "task_id": task_id,
        "new_status": new_status,
        "affected_rows": result.data.get("affected_rows", 0)
    })