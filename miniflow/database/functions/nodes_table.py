from ..core import execute_sql_query, fetch_all, fetch_one, handle_db_errors
from ..utils import generate_uuid, safe_json_dumps
from ..exceptions import Result


# Temel CRUD operasyonaları
@handle_db_errors("create node")
def create_node(db_path, workflow_id, name, type, script, params):
    node_id = generate_uuid()
    query = """
        INSERT INTO nodes (id, workflow_id, name, type, script, params)
        VALUES (?, ?, ?, ?, ?, ?)
        """
    result = execute_sql_query(
        db_path=db_path, 
        query=query, 
        params=(node_id, workflow_id, name, type, script, safe_json_dumps(params)))
    
    if not result.success:
        return Result.error(f"Failed to create node: {result.error}")
    return Result.success({"node_id": node_id})

@handle_db_errors("get node")
def get_node(db_path, node_id):
    query = "SELECT * FROM nodes WHERE id = ?"
    result = fetch_one(db_path=db_path, query=query, params=(node_id,))

    if not result.success:
        return Result.error(f"Failed to get node: {result.error}")
    return Result.success(result.data)

@handle_db_errors("delete node")
def delete_node(db_path, node_id):
    query = "DELETE FROM nodes WHERE id = ?"
    result = execute_sql_query(
        db_path=db_path, 
        query=query, 
        params=(node_id,))
    
    if not result.success:
        return Result.error(f"Failed to delete node: {result.error}")
    return Result.success({"deleted": True, "node_id": node_id})

@handle_db_errors("list nodes")
def list_nodes(db_path):
    query = "SELECT * FROM nodes"
    result = fetch_all(db_path=db_path, query=query, params=None)

    if not result.success:
        return Result.error(f"Failed to list nodes: {result.error}")
    return Result.success(result.data)

# Workflow tablosu ile bağlantılı işlemler
@handle_db_errors("list workflow nodes")
def list_workflow_nodes(db_path, workflow_id):
    query = "SELECT * FROM nodes WHERE workflow_id = ?"
    result = fetch_all(db_path=db_path, query=query, params=(workflow_id,))

    if not result.success:
        return Result.error(f"Failed to list workflow nodes: {result.error}")
    return Result.success(result.data)

@handle_db_errors("delete workflow nodes")
def delete_workflow_nodes(db_path, workflow_id):
    query = "DELETE FROM nodes WHERE workflow_id = ?"
    result = execute_sql_query(
        db_path=db_path, 
        query=query, 
        params=(workflow_id,))

    if not result.success:
        return Result.error(f"Failed to delete workflow nodes: {result.error}")
    return Result.success({"deleted": True, "workflow_id": workflow_id})

# Düğüm işlemleri 
@handle_db_errors("get node dependents")
def get_node_dependents(db_path, node_id):
    query = """
        SELECT n.id 
        FROM nodes n
        JOIN edges e ON n.id = e.to_node_id
        WHERE e.from_node_id = ?
        """
    result = fetch_all(db_path=db_path, query=query, params=(node_id,))
    
    if not result.success:
            return Result.error(f"Failed to get node dependents: {result.error}")
    
    node_ids = [row["id"] for row in result.data]
    return Result.success(node_ids)

@handle_db_errors("get node dependencies")
def get_node_dependencies(db_path, node_id):
    query = """
        SELECT n.id 
        FROM nodes n
        JOIN edges e ON n.id = e.from_node_id
        WHERE e.to_node_id = ?
        """
    result = fetch_all(db_path=db_path, query=query, params=(node_id,))
       
    if not result.success:
        return Result.error(f"Failed to get node dependencies: {result.error}")
        
    node_ids = [row["id"] for row in result.data]
    return Result.success(node_ids)