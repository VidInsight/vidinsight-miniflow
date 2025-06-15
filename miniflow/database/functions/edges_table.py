from ..core import execute_sql_query, fetch_all, fetch_one, handle_db_errors
from ..utils import generate_uuid, safe_json_dumps
from ..exceptions import Result

# Temel CRUD operasyonaları
@handle_db_errors("create edge")
def create_edge(db_path, workflow_id, from_node_id, to_node_id, condition_type='success'):
    edge_id = generate_uuid()
    query = """
        INSERT INTO edges (id, workflow_id, from_node_id, to_node_id, condition_type)
        VALUES (?, ?, ?, ?, ?)
        """
    result = execute_sql_query(
        db_path=db_path, 
        query=query, 
        params=(edge_id, workflow_id, from_node_id, to_node_id, condition_type))
        
    if not result.success:
        return Result.error(f"Failed to create edge: {result.error}")
    return Result.success({"edge_id": edge_id})

@handle_db_errors("get edge")
def get_edge(db_path, edge_id):
    query = "SELECT * FROM edges WHERE id = ?"
    result = fetch_one(db_path=db_path, query=query, params=(edge_id,))
    
    if not result.success:
        return Result.error(f"Failed to get edge: {result.error}")
    return Result.success(result.data)

@handle_db_errors("delete edge")
def delete_edge(db_path, edge_id):
    query = "DELETE FROM edges WHERE id = ?"
    result = execute_sql_query(
        db_path=db_path, 
        query=query, 
        params=(edge_id,))
    
    if not result.success:
        return Result.error(f"Failed to delete edge: {result.error}")
    return Result.success({"deleted": True, "edge_id": edge_id})

@handle_db_errors("list edges")
def list_edges(db_path):
    query = "SELECT * FROM edges"
    result = fetch_all(db_path=db_path, query=query, params=None)

    if not result.success:
        return Result.error(f"Failed to list edges: {result.error}")
    return Result.success(result.data)

# Workflow tablosu ile bağlantılı işlemler
@handle_db_errors("list workflow edges")
def list_workflow_edges(db_path, workflow_id):
    query = "SELECT * FROM edges WHERE workflow_id = ?"
    result = fetch_all(db_path=db_path, query=query, params=(workflow_id,))
    
    if not result.success:
        return Result.error(f"Failed to list workflow edges: {result.error}")
    return Result.success(result.data)

@handle_db_errors("delete workflow edges")
def delete_workflow_edges(db_path, workflow_id):
    query = "DELETE FROM edges WHERE workflow_id = ?"
    result = execute_sql_query(
        db_path=db_path, 
        query=query, 
        params=(workflow_id,))

    if not result.success:
        return Result.error(f"Failed to delete workflow edges: {result.error}")
    return Result.success({"deleted": True, "workflow_id": workflow_id})