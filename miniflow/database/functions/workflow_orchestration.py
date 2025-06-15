from ..core import handle_db_errors
from ..exceptions import Result
from ..utils import generate_timestamp, safe_json_dumps

# Import required functions from other modules
from .execution_results_table import create_record, combine_execution_records_results
from .execution_queue_table import decrease_dependency_count, list_execution_tasks, delete_execution_tasks, find_in_queue
from .executions_table import set_execution_status, set_execution_result, set_execution_end_time, check_execution_completion
from .nodes_table import get_node_dependents


@handle_db_errors("process execution result")
def process_execution_result(db_path, execution_id, node_id, status, result_data=None, error_message=None):
    """
    Amaç: Düğüm yürütme sonuçlarını işleyen ana orkestrasyon fonksiyonu, work_logic.txt'den workflow mantığını uygular.
    Döner: Başarılı ise işlenen sonuç bilgileri içeren Result objesi, hata durumunda hata mesajı içeren Result objesi.
    """
    # Step 1: Create execution result record (timestamps are handled internally)
    record_result = create_record(
        db_path=db_path,
        execution_id=execution_id,
        node_id=node_id,
        status=status,
        result_data=result_data,
        error_message=error_message
    )
    
    if not record_result.success:
        return record_result
    
    # Step 2: Handle based on result status
    if status == "failed":
        return handle_execution_failure(db_path, execution_id)
    elif status == "success":
        return handle_execution_success(db_path, execution_id, node_id)
    else:
        return Result.success({"processed": True, "record_id": record_result.data["record_id"]})


@handle_db_errors("finalize execution")
def finalize_execution(db_path, execution_id, final_status='completed'):
    """
    Amaç: Yürütmeyi sonlandırır için ortak yardımcı fonksiyon, uygun transaction benzeri davranış sağlar.
    Döner: Başarılı ise sonlandırma bilgileri ve final sonuçlar içeren Result objesi, hata durumunda hata mesajı.
    """
    # Step 1: Combine execution results into flat JSON format
    combine_result = combine_execution_records_results(db_path, execution_id)
    if not combine_result.success:
        return Result.error(f"Failed to combine execution results: {combine_result.error}")
    
    # Step 2: Update execution results (store the flat JSON)
    results_update = set_execution_result(db_path, execution_id, combine_result.data)
    if not results_update.success:
        return Result.error(f"Failed to update execution results: {results_update.error}")
    
    # Step 3: Update end time
    end_timestamp = generate_timestamp()
    end_time_result = set_execution_end_time(db_path, execution_id, end_timestamp)
    if not end_time_result.success:
        # Try to rollback results update if possible
        return Result.error(f"Failed to update execution end time: {end_time_result.error}")
    
    # Step 4: Update execution status to final status
    status_result = set_execution_status(db_path, execution_id, final_status)
    if not status_result.success:
        return Result.error(f"Failed to update execution status: {status_result.error}")
    
    return Result.success({
        "finalized": True,
        "execution_id": execution_id,
        "final_status": final_status,
        "final_results": combine_result.data,
        "completion_timestamp": end_timestamp
    })


@handle_db_errors("handle execution failure")
def handle_execution_failure(db_path, execution_id):
    """
    Amaç: İş akışı hata senaryosunu yönetir (work_logic.txt Bölüm 3), bekleyen görevleri iptal eder ve yürütmeyi sonlandırır.
    Döner: Başarılı ise iptal edilen görevler ve final sonuçlar içeren Result objesi, hata durumunda hata mesajı.
    """
    # Step 3.1: Cancel all pending tasks
    cancel_result = delete_execution_tasks(db_path, execution_id)
    if not cancel_result.success:
        return Result.error(f"Failed to cancel execution tasks: {cancel_result.error}")
    
    # Steps 3.2-3.6: Finalize execution
    finalize_result = finalize_execution(db_path, execution_id, 'completed')
    if not finalize_result.success:
        return finalize_result
    
    return Result.success({
        "execution_failed": True,
        "execution_id": execution_id,
        "cancelled_tasks": cancel_result.data.get("cancelled_tasks", 0),
        "deleted_tasks": cancel_result.data.get("deleted_tasks", 0),
        "final_results": finalize_result.data["final_results"],
        "completion_timestamp": finalize_result.data["completion_timestamp"]
    })


@handle_db_errors("batch update dependencies")
def batch_update_dependencies(db_path, execution_id, dependent_node_ids):
    """
    Amaç: Birden fazla düğüm için bağımlılık sayılarını doğrulama ile toplu günceller.
    Döner: Başarılı ise güncellenen görev listesi içeren Result objesi, hata durumunda hata mesajı içeren Result objesi.
    """
    updated_tasks = []
    
    for dependent_node_id in dependent_node_ids:
        # Validate dependent node exists in execution queue
        task_result = find_in_queue(db_path, execution_id, dependent_node_id)
        if not task_result.success:
            # Log but don't fail - dependent might have been completed already
            continue
            
        if not task_result.data:
            # Node not found in queue - likely already completed, skip
            continue
            
        task_id = task_result.data["id"]
        
        # Decrease dependency count
        decrease_result = decrease_dependency_count(db_path, task_id)
        if decrease_result.success:
            updated_tasks.append({
                "task_id": task_id,
                "node_id": dependent_node_id,
                "old_dependency_count": decrease_result.data.get("old_dependency_count", 0),
                "new_dependency_count": decrease_result.data.get("new_dependency_count", 0),
                "became_ready": decrease_result.data.get("became_ready", False)
            })
        else:
            # Log error but continue with other dependencies
            pass
    
    return Result.success(updated_tasks)


@handle_db_errors("handle execution success")
def handle_execution_success(db_path, execution_id, completed_node_id):
    """
    Amaç: Başarılı düğüm yürütmesini yönetir (work_logic.txt Bölüm 4), bağımlılıkları günceller ve tamamlanma kontrolü yapar.
    Döner: Başarılı ise güncellenmiş görev bilgileri veya tamamlanma durumu içeren Result objesi, hata durumunda hata mesajı.
    """
    # Step 4.1: Get dependent nodes and validate they exist
    dependents_result = get_node_dependents(db_path, completed_node_id)
    if not dependents_result.success:
        return Result.error(f"Failed to get node dependents: {dependents_result.error}")
    
    dependent_node_ids = dependents_result.data
    
    # Batch update dependency counts with validation
    batch_update_result = batch_update_dependencies(db_path, execution_id, dependent_node_ids)
    if not batch_update_result.success:
        return Result.error(f"Failed to update dependencies: {batch_update_result.error}")
    
    updated_tasks = batch_update_result.data
    
    # Step 4.2: Check if execution is complete (no more pending/ready/running tasks)
    completion_result = check_execution_completion(db_path, execution_id)
    if not completion_result.success:
        return Result.error(f"Failed to check execution completion: {completion_result.error}")
    
    if completion_result.data["is_complete"]:
        # Steps 4.2.1-4.2.5: Handle execution completion
        return complete_execution(db_path, execution_id)
    else:
        # Step 4.3: Continue with updated dependencies
        return Result.success({
            "node_completed": True,
            "completed_node_id": completed_node_id,
            "updated_tasks": updated_tasks,
            "execution_continues": True,
            "remaining_tasks": completion_result.data.get("status_counts", {})
        })


@handle_db_errors("complete execution")
def complete_execution(db_path, execution_id):
    """
    Amaç: Tüm görevler tamamlandığında iş akışı yürütmesini bitirir, ortak finalize_execution yardımcısını kullanır.
    Döner: Başarılı ise tamamlanma onayı ve final sonuçlar içeren Result objesi, hata durumunda hata mesajı.
    """
    finalize_result = finalize_execution(db_path, execution_id, 'completed')
    if not finalize_result.success:
        return finalize_result
    
    return Result.success({
        "execution_completed": True,
        "execution_id": execution_id,
        "final_results": finalize_result.data["final_results"],
        "completion_timestamp": finalize_result.data["completion_timestamp"]
    })


@handle_db_errors("trigger workflow execution")
def trigger_workflow_execution(db_path, workflow_id):
    """
    Amaç: İş akışı yürütmesini başlatan ana tetikleyici fonksiyon, work_logic.txt TRIGGER bölümünü uygular.
    Döner: Başarılı ise execution_id ve oluşturulan görev bilgileri içeren Result objesi, hata durumunda hata mesajı.
    """
    from .executions_table import start_execution
    from .execution_queue_table import reorder_execution_queue
    
    # Steps 1-3: Start execution (creates execution record and queues all tasks)
    start_result = start_execution(db_path, workflow_id)
    if not start_result.success:
        return Result.error(f"Failed to start workflow execution: {start_result.error}")
    
    execution_id = start_result.data["execution_id"]
    
    # Initial queue reordering (makes tasks with dependency_count=0 ready)
    reorder_result = reorder_execution_queue(db_path)
    if not reorder_result.success:
        return Result.error(f"Failed initial queue reorder: {reorder_result.error}")
    
    return Result.success({
        "workflow_triggered": True,
        "workflow_id": workflow_id,
        "execution_id": execution_id,
        "created_tasks": start_result.data["task_count"],
        "ready_tasks": reorder_result.data["ready_count"],
        "trigger_timestamp": generate_timestamp()
    })


@handle_db_errors("get execution status summary")
def get_execution_status_summary(db_path, execution_id):
    """
    Amaç: Bir yürütme için kapsamlı durum özeti alır, görev ve sonuç istatistikleri derler.
    Döner: Başarılı ise execution detayları ve istatistikler içeren Result objesi, hata durumunda hata mesajı.
    """
    from .executions_table import get_execution
    from .execution_queue_table import list_execution_tasks
    from .execution_results_table import list_execution_records
    
    # Get execution details
    execution_result = get_execution(db_path, execution_id)
    if not execution_result.success:
        return Result.error(f"Failed to get execution: {execution_result.error}")
    
    # Get task status
    tasks_result = list_execution_tasks(db_path, execution_id)
    if not tasks_result.success:
        return Result.error(f"Failed to get execution tasks: {tasks_result.error}")
    
    # Get execution results
    results_result = list_execution_records(db_path, execution_id)
    if not results_result.success:
        return Result.error(f"Failed to get execution results: {results_result.error}")
    
    # Compile summary
    task_status_counts = {}
    for task in tasks_result.data:
        status = task["status"]
        task_status_counts[status] = task_status_counts.get(status, 0) + 1
    
    result_status_counts = {}
    for result in results_result.data:
        status = result["status"]
        result_status_counts[status] = result_status_counts.get(status, 0) + 1
    
    return Result.success({
        "execution": execution_result.data,
        "task_counts": task_status_counts,
        "result_counts": result_status_counts,
        "total_tasks": len(tasks_result.data),
        "total_results": len(results_result.data),
        "summary_timestamp": generate_timestamp()
    })


@handle_db_errors("get ready tasks for execution")
def get_ready_tasks_for_execution(db_path, execution_id, limit=10):
    """
    Amaç: Belirtilen yürütme için anında çalıştırılabilir hazır görevleri getirir, öncelik sıralaması yapar.
    Döner: Başarılı ise hazır görev listesi içeren Result objesi, hata durumunda hata mesajı içeren Result objesi.
    """
    from .execution_queue_table import list_execution_tasks
    
    # Get ready tasks for this execution
    tasks_result = list_execution_tasks(db_path, execution_id, status='ready')
    if not tasks_result.success:
        return tasks_result
    
    # Sort by priority and limit results
    ready_tasks = sorted(tasks_result.data, key=lambda x: x.get('priority', 0), reverse=True)
    limited_tasks = ready_tasks[:limit] if limit else ready_tasks
    
    return Result.success({
        "execution_id": execution_id,
        "ready_tasks": limited_tasks,
        "ready_count": len(limited_tasks),
        "total_ready": len(ready_tasks)
    })


@handle_db_errors("mark task as running")
def mark_task_as_running(db_path, task_id):
    """
    Amaç: Yürütme başladığında görevi çalışıyor durumuna işaretler.
    Döner: Başarılı ise güncelleme onayı ve zaman damgası içeren Result objesi, hata durumunda hata mesajı.
    """
    from .execution_queue_table import update_task_status
    
    result = update_task_status(db_path, task_id, 'running')
    if not result.success:
        return Result.error(f"Failed to mark task as running: {result.error}")
    
    return Result.success({
        "task_id": task_id,
        "new_status": "running",
        "timestamp": generate_timestamp()
    })


@handle_db_errors("create workflow with components")
def create_workflow_with_components(db_path, workflow_data):
    """
    Amaç: Düğümler, kenarlar ve tetikleyicilerle birlikte eksiksiz bir iş akışı oluşturur, kapsamlı doğrulama yapar.
    Döner: Başarılı ise workflow_id ve oluşturulan bileşen sayıları içeren Result objesi, hata durumunda hata mesajı.
    """
    from .workflows_table import create_workflow
    from .nodes_table import create_node
    from .edges_table import create_edge
    from .triggers_table import create_trigger
    
    # Validate basic structure
    if not isinstance(workflow_data, dict):
        return Result.error("Workflow data must be a dictionary")
    
    if "workflow" not in workflow_data or "nodes" not in workflow_data:
        return Result.error("Missing required keys: workflow, nodes")
    
    workflow_info = workflow_data["workflow"]
    nodes_data = workflow_data["nodes"]
    edges_data = workflow_data.get("edges", [])
    triggers_data = workflow_data.get("triggers", [])
    
    if not workflow_info.get("name"):
        return Result.error("Workflow name is required")
    
    if not nodes_data or len(nodes_data) == 0:
        return Result.error("At least one node is required")
    
    # Step 1: Create workflow
    workflow_result = create_workflow(
        db_path=db_path,
        name=workflow_info["name"],
        description=workflow_info.get("description"),
        version=workflow_info.get("version", 1)
    )
    
    if not workflow_result.success:
        return Result.error(f"Failed to create workflow: {workflow_result.error}")
    
    workflow_id = workflow_result.data["workflow_id"]
    
    # Step 2: Create nodes
    node_ids = []
    for i, node_data in enumerate(nodes_data):
        if not node_data.get("name") or not node_data.get("type"):
            return Result.error(f"Node {i} missing name or type")
        
        node_result = create_node(
            db_path=db_path,
            workflow_id=workflow_id,
            name=node_data["name"],
            type=node_data["type"],
            script=node_data.get("script", ""),
            params=node_data.get("params", {})
        )
        
        if not node_result.success:
            return Result.error(f"Failed to create node {i}: {node_result.error}")
        
        node_ids.append(node_result.data["node_id"])
    
    # Step 3: Create edges
    edge_ids = []
    for i, edge_data in enumerate(edges_data):
        if "from_node" not in edge_data or "to_node" not in edge_data:
            return Result.error(f"Edge {i} missing from_node or to_node")
        
        from_index = edge_data["from_node"]
        to_index = edge_data["to_node"]
        
        if from_index >= len(node_ids) or to_index >= len(node_ids):
            return Result.error(f"Edge {i} has invalid node index")
        
        edge_result = create_edge(
            db_path=db_path,
            workflow_id=workflow_id,
            from_node_id=node_ids[from_index],
            to_node_id=node_ids[to_index],
            condition_type=edge_data.get("condition_type", "success")
        )
        
        if not edge_result.success:
            return Result.error(f"Failed to create edge {i}: {edge_result.error}")
        
        edge_ids.append(edge_result.data["edge_id"])
    
    # Step 4: Create triggers
    trigger_ids = []
    for i, trigger_data in enumerate(triggers_data):
        if not trigger_data.get("trigger_type"):
            return Result.error(f"Trigger {i} missing trigger_type")
        
        trigger_result = create_trigger(
            db_path=db_path,
            workflow_id=workflow_id,
            trigger_type=trigger_data["trigger_type"],
            config=trigger_data.get("config", {})
        )
        
        if not trigger_result.success:
            return Result.error(f"Failed to create trigger {i}: {trigger_result.error}")
        
        trigger_ids.append(trigger_result.data["trigger_id"])
    
    # Return result
    return Result.success({
        "workflow_id": workflow_id,
        "nodes_created": len(node_ids),
        "edges_created": len(edge_ids),
        "triggers_created": len(trigger_ids)
    }) 