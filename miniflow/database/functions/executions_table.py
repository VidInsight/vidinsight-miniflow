from ..core import execute_sql_query, fetch_all, fetch_one, handle_db_errors
from ..utils import generate_uuid, safe_json_dumps, generate_timestamp
from ..exceptions import Result


# Helper function for validation
def _validate_workflow_exists(db_path, workflow_id):
    """
    Amaç: Belirtilen workflow ID'nin veritabanında mevcut olup olmadığını kontrol eder.
    Döner: Workflow mevcutsa True, yoksa False döner.
    """
    query = "SELECT id FROM workflows WHERE id = ?"
    result = fetch_one(db_path, query, (workflow_id,))
    return result.success and result.data is not None


# Temel CRUD operasyonaları
@handle_db_errors("create execution")
def create_execution(db_path, workflow_id):
    """
    Amaç: Belirtilen workflow için yeni bir yürütme kaydı oluşturur, workflow varlığını doğrular.
    Döner: Başarılı ise execution_id içeren Result objesi, hata durumunda hata mesajı içeren Result objesi.
    """
    # Validate workflow exists
    if not _validate_workflow_exists(db_path, workflow_id):
        return Result.error(f"Workflow not found: {workflow_id}")
    
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
    """
    Amaç: Belirtilen ID'ye sahip yürütmenin tüm bilgilerini getirir.
    Döner: Başarılı ise execution verilerini içeren Result objesi, bulunamazsa None, hata durumunda hata mesajı.
    """
    query = "SELECT * FROM executions WHERE id = ?"
    result = fetch_one(db_path=db_path, query=query, params=(execution_id,))

    if not result.success:
        return Result.error(f"Failed to get execution: {result.error}")
    return Result.success(result.data)

@handle_db_errors("delete executions")
def delete_execution(db_path, execution_id):
    """
    Amaç: Belirtilen yürütmeyi veritabanından siler, önce varlığını kontrol eder.
    Döner: Başarılı ise silme onayı içeren Result objesi, hata durumunda hata mesajı içeren Result objesi.
    """
    # Check if execution exists first
    check_result = get_execution(db_path, execution_id)
    if not check_result.success:
        return check_result
    
    if not check_result.data:
        return Result.error(f"Execution not found: {execution_id}")
    
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
    """
    Amaç: Yürütmeleri workflow ve durum filtreleri ile listeler, sayfalama desteği sağlar.
    Döner: Başarılı ise execution listesi içeren Result objesi, hata durumunda hata mesajı içeren Result objesi.
    """
    query = "SELECT * FROM executions"
    params = []
    conditions = []
    
    if workflow_id:
        # Validate workflow exists if filtering by workflow
        if not _validate_workflow_exists(db_path, workflow_id):
            return Result.error(f"Workflow not found: {workflow_id}")
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
    """
    Amaç: Belirtilen yürütmenin bitiş zamanını günceller, execution varlığını doğrular.
    Döner: Başarılı ise güncelleme onayı içeren Result objesi, hata durumunda hata mesajı içeren Result objesi.
    """
    # Validate execution exists
    if not get_execution(db_path, execution_id).data:
        return Result.error(f"Execution not found: {execution_id}")
    
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
        return Result.error(f"Failed to update execution end time: {result.error}")
    return Result.success({"updated": True})

@handle_db_errors("set execution status")
def set_execution_status(db_path, execution_id, status_update):
    """
    Amaç: Yürütme durumunu günceller, durum geçerliliğini ve execution varlığını doğrular.
    Döner: Başarılı ise güncelleme onayı içeren Result objesi, hata durumunda hata mesajı içeren Result objesi.
    """
    # Validate execution exists
    if not get_execution(db_path, execution_id).data:
        return Result.error(f"Execution not found: {execution_id}")
    
    # Validate status value
    valid_statuses = ['pending', 'running', 'completed', 'failed', 'cancelled']
    if status_update not in valid_statuses:
        return Result.error(f"Invalid status: {status_update}. Valid statuses: {valid_statuses}")
    
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
    else:
        # For 'pending' status
        query = """
        UPDATE executions 
        SET status = ? 
        WHERE id = ?
        """
        params = (status_update, execution_id)

    result = execute_sql_query(
        db_path=db_path, 
        query=query,
        params=params)
    
    if not result.success:
        return Result.error(f"Failed to update execution status: {result.error}")
    return Result.success({"updated": True})

@handle_db_errors("set execution result")
def set_execution_result(db_path, execution_id, execution_result):
    """
    Amaç: Yürütme sonuçlarını JSON formatında günceller, execution varlığını doğrular.
    Döner: Başarılı ise güncelleme onayı içeren Result objesi, hata durumunda hata mesajı içeren Result objesi.
    """
    # Validate execution exists
    if not get_execution(db_path, execution_id).data:
        return Result.error(f"Execution not found: {execution_id}")
    
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
    """
    Amaç: İş akışı yürütmesini başlatır, execution kaydı oluşturur ve görevleri kuyruğa alır, transaction güvenliği sağlar.
    Döner: Başarılı ise execution_id ve oluşturulan görev bilgileri içeren Result objesi, hata durumunda rollback ile hata mesajı.
    """
    from ..functions.nodes_table import list_workflow_nodes
    from ..functions.execution_queue_table import create_task
    from ..functions.edges_table import list_workflow_edges
    
    # Validate workflow exists first
    if not _validate_workflow_exists(db_path, workflow_id):
        return Result.error(f"Workflow not found: {workflow_id}")
    
    try:
        # Step 1: Create execution record
        execution_result = create_execution(db_path, workflow_id)
        if not execution_result.success:
            return execution_result
        
        execution_id = execution_result.data["execution_id"]
        
        # Step 2: Get all workflow nodes
        nodes_result = list_workflow_nodes(db_path, workflow_id)
        if not nodes_result.success:
            # Rollback: delete the execution we just created
            delete_execution(db_path, execution_id)
            return Result.error(f"Failed to get workflow nodes: {nodes_result.error}")
        
        # Validate workflow has nodes
        if not nodes_result.data:
            delete_execution(db_path, execution_id)
            return Result.error("Cannot start execution: workflow has no nodes")
        
        # Step 3: Calculate dependency counts for each node
        dependency_counts = {}
        edges_result = list_workflow_edges(db_path, workflow_id)
        if not edges_result.success:
            delete_execution(db_path, execution_id)
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
        failed_task_creation = False
        
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
                failed_task_creation = True
                break
            
            created_tasks.append({
                "task_id": task_result.data["queue_id"],
                "node_id": node_id,
                "dependency_count": dependency_count
            })
        
        # If task creation failed, rollback everything
        if failed_task_creation:
            # Clean up created tasks and execution
            from ..functions.execution_queue_table import delete_execution_tasks
            delete_execution_tasks(db_path, execution_id)  # Clean up any tasks created
            delete_execution(db_path, execution_id)  # Clean up execution
            return Result.error("Failed to create all tasks - execution rolled back")
        
        # Step 5: Update execution status to running
        status_result = set_execution_status(db_path, execution_id, 'running')
        if not status_result.success:
            # Rollback: clean up tasks and execution
            from ..functions.execution_queue_table import delete_execution_tasks
            delete_execution_tasks(db_path, execution_id)
            delete_execution(db_path, execution_id)
            return Result.error(f"Failed to update execution status: {status_result.error}")
        
        return Result.success({
            "execution_id": execution_id,
            "workflow_id": workflow_id,
            "created_tasks": created_tasks,
            "task_count": len(created_tasks),
            "ready_tasks": len([t for t in created_tasks if t["dependency_count"] == 0])
        })
        
    except Exception as e:
        # Catch any unexpected errors and attempt cleanup
        try:
            if 'execution_id' in locals():
                from ..functions.execution_queue_table import delete_execution_tasks
                delete_execution_tasks(db_path, execution_id)
                delete_execution(db_path, execution_id)
        except:
            pass  # If cleanup fails, at least we tried
        
        return Result.error(f"Unexpected error during execution start: {str(e)}")

@handle_db_errors("stop execution")
def stop_execution(db_path, execution_id):
    """
    Amaç: Çalışan bir yürütmeyi durdurur ve bekleyen görevleri iptal eder, durum kontrolü yapar.
    Döner: Başarılı ise iptal edilen görev bilgileri içeren Result objesi, hata durumunda hata mesajı içeren Result objesi.
    """
    # Validate execution exists
    execution_data = get_execution(db_path, execution_id)
    if not execution_data.success or not execution_data.data:
        return Result.error(f"Execution not found: {execution_id}")
    
    # Check execution status
    current_status = execution_data.data.get("status")
    if current_status in ['completed', 'failed', 'cancelled']:
        return Result.error(f"Cannot stop execution: already {current_status}")
    
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
    """
    Amaç: Kalan görevleri inceleyerek yürütmenin tamamlanıp tamamlanmadığını kontrol eder.
    Döner: Başarılı ise tamamlanma durumu ve görev istatistikleri içeren Result objesi, hata durumunda hata mesajı.
    """
    # Validate execution exists
    if not get_execution(db_path, execution_id).data:
        return Result.error(f"Execution not found: {execution_id}")
    
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

