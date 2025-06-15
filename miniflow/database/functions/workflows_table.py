from ..core import execute_sql_query, fetch_all, fetch_one, handle_db_errors
from ..utils import generate_uuid, safe_json_dumps, generate_timestamp
from ..exceptions import Result


# Temel CRUD operasyonaları
@handle_db_errors("create workflow")
def create_workflow(db_path, name, description=None, version=1):
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
    query = "SELECT * FROM workflows WHERE id = ?"
    result = fetch_one(db_path=db_path, query=query, params=(workflow_id,))

    if not result.success:
        return Result.error(f"Failed to get workflow: {result.error}")
    return Result.success(result.data)

@handle_db_errors("delete workflow")
def delete_workflow(db_path, workflow_id):
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
    Lists workflows with pagination.
    Note: Removed status filtering as workflows table doesn't have a status field.
    Workflow status is determined by active executions, not stored in workflows table.
    """
    query = "SELECT * FROM workflows ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params = [limit, offset]
    result = fetch_all(db_path=db_path, query=query, params=params)
        
    if not result.success:
        return Result.error(f"Failed to list workflows: {result.error}")
    return Result.success(result.data)