from ..core import execute_sql_query, fetch_all, fetch_one, handle_db_errors
from ..utils import generate_uuid, safe_json_dumps, generate_timestamp
from ..exceptions import Result


# Temel CRUD operasyonaları
@handle_db_errors("create task")
def create_task(db_path, execution_id, node_id, dependency_count, priority=0):
    """
    Amaç: Yürütme kuyruğuna yeni görev ekler, bağımlılık sayısına göre otomatik durum atar.
    Döner: Başarılı ise queue_id içeren Result objesi, hata durumunda hata mesajı içeren Result objesi.
    """
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
    """
    Amaç: Belirtilen ID'ye sahip görevin tüm bilgilerini getirir.
    Döner: Başarılı ise task verilerini içeren Result objesi, bulunamazsa None, hata durumunda hata mesajı.
    """
    query = "SELECT * FROM execution_queue WHERE id = ?"
    result = fetch_one(db_path=db_path, query=query, params=(task_id,))

    if not result.success:
        return Result.error(f"Failed to get task: {result.error}")
    return Result.success(result.data)

@handle_db_errors("delete task")
def delete_task(db_path, task_id):
    """
    Amaç: Belirtilen görevi yürütme kuyruğundan siler.
    Döner: Başarılı ise silme onayı içeren Result objesi, hata durumunda hata mesajı içeren Result objesi.
    """
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
    """
    Amaç: Tüm yürütmelerdeki görevleri durum filtresi ile listeler, node bilgileri ile birleştirir.
    Döner: Başarılı ise task listesi içeren Result objesi, hata durumunda hata mesajı içeren Result objesi.
    """
    query = """
    SELECT eq.*, n.name as node_name, n.type as node_type
    FROM execution_queue eq
    JOIN nodes n ON eq.node_id = n.id
    """
    params = []
    
    if status:
        query += " WHERE eq.status = ?"
        params.append(status)
    
    query += " ORDER BY eq.priority DESC, eq.dependency_count ASC"
    result = fetch_all(db_path=db_path, query=query, params=params)
    
    if not result.success:
        return Result.error(f"Failed to list tasks: {result.error}")
    return Result.success(result.data)

@handle_db_errors("count tasks")
def count_tasks(db_path, execution_id, status=None):
    """
    Amaç: Belirtilen yürütmeye ait görevleri sayar, durum filtresi ile filtreleme yapabilir.
    Döner: Başarılı ise görev sayısı içeren Result objesi, hata durumunda hata mesajı içeren Result objesi.
    """
    query = "SELECT COUNT(*) as count FROM execution_queue WHERE execution_id = ?"
    params = [execution_id]
    
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
    """
    Amaç: Belirtilen yürütmeye ait görevleri durum filtresi ile listeler, node detayları ile birleştirir.
    Döner: Başarılı ise execution'a özel task listesi içeren Result objesi, hata durumunda hata mesajı.
    """
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
    """
    Amaç: Belirtilen yürütmeye ait görevleri iptal eder ve siler, running/completed görevleri korur.
    Döner: Başarılı ise iptal edilen ve silinen görev sayılarını içeren Result objesi, hata durumunda hata mesajı.
    """
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
    """
    Amaç: Belirtilen yürütme ve düğüm ID'si ile görevi kuyruğta bulur.
    Döner: Başarılı ise task verilerini içeren Result objesi, bulunamazsa None, hata durumunda hata mesajı.
    """
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
    """
    Amaç: Yürütme kuyruğunu yeniden düzenler, bağımlılığı olmayan görevleri hazır duruma getirir.
    Döner: Başarılı ise güncellenen görev sayısı ve hazır görev listesi içeren Result objesi, hata durumunda hata mesajı.
    """
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
    """
    Amaç: Görevin bağımlılık sayısını azaltır ve sıfıra ulaşırsa durumunu hazır yapar.
    Döner: Başarılı ise eski/yeni bağımlılık sayıları ve durum bilgileri içeren Result objesi, hata durumunda hata mesajı.
    """
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
    """
    Amaç: Belirtilen görevin durumunu günceller.
    Döner: Başarılı ise güncelleme onayı ve etkilenen satır sayısı içeren Result objesi, hata durumunda hata mesajı.
    """
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


# Batch Processing Fonksiyonları (Performans Optimizasyonu)
@handle_db_errors("batch mark tasks as running")
def batch_mark_tasks_as_running(db_path, task_ids):
    """
    Amaç: Birden fazla task'ı aynı anda 'running' durumuna getirir (batch processing)
    Döner: Başarılı ise güncellenen task sayısı içeren Result objesi, hata durumunda hata mesajı
    """
    if not task_ids:
        return Result.success({"updated_count": 0, "task_ids": []})
    
    # Parametrized query için placeholder'lar oluştur
    placeholders = ','.join(['?' for _ in task_ids])
    
    query = f"""
    UPDATE execution_queue 
    SET status = 'running' 
    WHERE id IN ({placeholders}) AND status = 'ready'
    """
    
    # 'running' parametresini task_ids'nin başına ekle
    params = ['running'] + list(task_ids)
    # Düzeltme: parametreler zaten query'de doğru
    params = list(task_ids)
    
    result = execute_sql_query(db_path=db_path, query=query, params=params)
    
    if not result.success:
        return Result.error(f"Failed to batch mark tasks as running: {result.error}")
    
    updated_count = result.data.get("affected_rows", 0)
    
    return Result.success({
        "updated_count": updated_count,
        "task_ids": task_ids[:updated_count],  # Sadece başarılı olanlar
        "batch_size": len(task_ids)
    })


@handle_db_errors("batch delete tasks")  
def batch_delete_tasks(db_path, task_ids):
    """
    Amaç: Birden fazla task'ı aynı anda siler (batch processing)
    Döner: Başarılı ise silinen task sayısı içeren Result objesi, hata durumunda hata mesajı
    """
    if not task_ids:
        return Result.success({"deleted_count": 0, "task_ids": []})
    
    # Parametrized query için placeholder'lar oluştur
    placeholders = ','.join(['?' for _ in task_ids])
    
    query = f"DELETE FROM execution_queue WHERE id IN ({placeholders})"
    
    result = execute_sql_query(db_path=db_path, query=query, params=list(task_ids))
    
    if not result.success:
        return Result.error(f"Failed to batch delete tasks: {result.error}")
    
    deleted_count = result.data.get("affected_rows", 0)
    
    return Result.success({
        "deleted_count": deleted_count,
        "task_ids": task_ids[:deleted_count],
        "batch_size": len(task_ids)
    })


@handle_db_errors("batch create tasks")
def batch_create_tasks(db_path, execution_id, node_data_list):
    """
    Amaç: Birden fazla task'ı aynı anda oluşturur (batch processing)
    Args:
        node_data_list: List of dicts with keys: node_id, dependency_count, priority
    Döner: Başarılı ise oluşturulan task'ların ID'leri içeren Result objesi
    """
    if not node_data_list:
        return Result.success({"created_tasks": [], "created_count": 0})
    
    # Bulk insert için değerleri hazırla
    task_data = []
    task_ids = []
    
    for node_data in node_data_list:
        task_id = generate_uuid()
        task_ids.append(task_id)
        
        dependency_count = node_data.get('dependency_count', 0)
        priority = node_data.get('priority', 0)
        initial_status = 'ready' if dependency_count == 0 else 'pending'
        
        task_data.append((
            task_id,
            execution_id, 
            node_data['node_id'],
            initial_status,
            priority,
            dependency_count
        ))
    
    # Bulk insert query
    query = """
    INSERT INTO execution_queue 
    (id, execution_id, node_id, status, priority, dependency_count)
    VALUES (?, ?, ?, ?, ?, ?)
    """
    
    # Multiple insert işlemi
    success_count = 0
    created_ids = []
    
    for task_tuple in task_data:
        result = execute_sql_query(db_path=db_path, query=query, params=task_tuple)
        if result.success:
            success_count += 1
            created_ids.append(task_tuple[0])  # task_id
    
    return Result.success({
        "created_count": success_count,
        "created_tasks": created_ids,
        "total_requested": len(node_data_list)
    })