from ..core import execute_sql_query, fetch_all, fetch_one, handle_db_errors
from ..utils import generate_uuid, safe_json_dumps, generate_timestamp
from ..exceptions import Result


# Temel CRUD operasyonaları
@handle_db_errors("create workflow")
def create_workflow(db_path, name, description=None, version=1):
    """
    Amaç: Yeni bir iş akışı oluşturur ve benzersiz ID ile veritabanına kaydeder.
    Döner: Başarılı ise workflow_id içeren Result objesi, hata durumunda hata mesajı içeren Result objesi.
    """
    workflow_id = generate_uuid()
    timestamp = generate_timestamp()

    query = """
    INSERT INTO workflows (id, name, description, version, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, ?)
    """
    
    result = execute_sql_query(
        db_path=db_path, 
        query=query, 
        params=(workflow_id, name, description, version, timestamp, timestamp))

    if not result.success:
        return Result.error(f"Failed to create workflow: {result.error}")
    return Result.success({"workflow_id": workflow_id})

@handle_db_errors("get workflow")
def get_workflow(db_path, workflow_id):
    """
    Amaç: Belirtilen ID'ye sahip iş akışının tüm bilgilerini getirir.
    Döner: Başarılı ise workflow verilerini içeren Result objesi, bulunamazsa None, hata durumunda hata mesajı.
    """
    query = "SELECT * FROM workflows WHERE id = ?"
    result = fetch_one(db_path=db_path, query=query, params=(workflow_id,))

    if not result.success:
        return Result.error(f"Failed to get workflow: {result.error}")
    return Result.success(result.data)

@handle_db_errors("delete workflow")
def delete_workflow(db_path, workflow_id):
    """
    Amaç: Belirtilen iş akışını ve tüm ilişkili kayıtları CASCADE ile siler.
    Döner: Başarılı ise silme onayı içeren Result objesi, hata durumunda hata mesajı içeren Result objesi.
    """
    # Foreign key CASCADE ile otomatik olarak tüm ilişkili kayıtlar silinir
    query = "DELETE FROM workflows WHERE id = ?"
    result = execute_sql_query(
        db_path=db_path, 
        query=query, 
        params=(workflow_id,))
        
    if not result.success:
        return Result.error(f"Failed to delete workflow: {result.error}")
    return Result.success({"deleted": True, "workflow_id": workflow_id})

@handle_db_errors("list workflows")
def list_workflows(db_path, limit=100, offset=0):
    """
    Amaç: Veritabanındaki tüm iş akışlarını sayfalama ile listeler, en yeni olanlar önce gelir.
    Döner: Başarılı ise workflow listesi içeren Result objesi, hata durumunda hata mesajı içeren Result objesi.
    """
    query = "SELECT * FROM workflows ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params = [limit, offset]
    result = fetch_all(db_path=db_path, query=query, params=params)
        
    if not result.success:
        return Result.error(f"Failed to list workflows: {result.error}")
    return Result.success(result.data)