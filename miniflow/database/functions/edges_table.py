from ..core import execute_sql_query, fetch_all, fetch_one, handle_db_errors
from ..utils import generate_uuid, safe_json_dumps
from ..exceptions import Result

# Helper functions for validation
def _validate_workflow_exists(db_path, workflow_id):
    """Helper function to validate workflow exists"""
    query = "SELECT id FROM workflows WHERE id = ?"
    result = fetch_one(db_path, query, (workflow_id,))
    return result.success and result.data is not None

def _validate_node_exists(db_path, node_id):
    """Helper function to validate node exists and return its workflow_id"""
    query = "SELECT workflow_id FROM nodes WHERE id = ?"
    result = fetch_one(db_path, query, (node_id,))
    if result.success and result.data:
        return result.data["workflow_id"]
    return None

def _validate_nodes_same_workflow(db_path, from_node_id, to_node_id):
    """Validates that both nodes exist and belong to the same workflow"""
    from_workflow = _validate_node_exists(db_path, from_node_id)
    to_workflow = _validate_node_exists(db_path, to_node_id)
    
    if not from_workflow:
        return False, f"From node not found: {from_node_id}"
    if not to_workflow:
        return False, f"To node not found: {to_node_id}"
    if from_workflow != to_workflow:
        return False, f"Nodes belong to different workflows: {from_workflow} vs {to_workflow}"
    
    return True, from_workflow

def _edge_would_create_cycle(db_path, from_node_id, to_node_id):
    """Check if adding this edge would create a cycle"""
    # Simple cycle detection: check if there's already a path from to_node to from_node
    # This is a basic implementation - for production, consider more sophisticated cycle detection
    
    # If to_node_id can reach from_node_id, adding this edge would create a cycle
    def can_reach(start_node, target_node, visited=None):
        if visited is None:
            visited = set()
        
        if start_node in visited:
            return False
        visited.add(start_node)
        
        if start_node == target_node:
            return True
        
        # Get all nodes that start_node points to
        query = "SELECT to_node_id FROM edges WHERE from_node_id = ?"
        result = fetch_all(db_path, query, (start_node,))
        
        if not result.success:
            return False
        
        for row in result.data:
            if can_reach(row["to_node_id"], target_node, visited.copy()):
                return True
        
        return False
    
    return can_reach(to_node_id, from_node_id)

# Temel CRUD operasyonaları
@handle_db_errors("create edge")
def create_edge(db_path, workflow_id, from_node_id, to_node_id, condition_type='success'):
    """Creates an edge between two nodes with comprehensive validation"""
    # Validate workflow exists
    if not _validate_workflow_exists(db_path, workflow_id):
        return Result.error(f"Workflow not found: {workflow_id}")
    
    # Validate both nodes exist and belong to the same workflow
    is_valid, workflow_or_error = _validate_nodes_same_workflow(db_path, from_node_id, to_node_id)
    if not is_valid:
        return Result.error(workflow_or_error)
    
    # Ensure the nodes belong to the specified workflow
    if workflow_or_error != workflow_id:
        return Result.error(f"Nodes belong to workflow {workflow_or_error}, not {workflow_id}")
    
    # Prevent self-loops
    if from_node_id == to_node_id:
        return Result.error("Cannot create edge from node to itself")
    
    # Check for duplicate edges
    duplicate_check = """
    SELECT id FROM edges 
    WHERE workflow_id = ? AND from_node_id = ? AND to_node_id = ? AND condition_type = ?
    """
    duplicate_result = fetch_one(db_path, duplicate_check, (workflow_id, from_node_id, to_node_id, condition_type))
    if duplicate_result.success and duplicate_result.data:
        return Result.error("Edge already exists between these nodes with this condition type")
    
    # Check for cycle creation
    if _edge_would_create_cycle(db_path, from_node_id, to_node_id):
        return Result.error("Cannot create edge: would create a cycle in the workflow")
    
    # Create the edge
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
    # Check if edge exists first
    check_result = get_edge(db_path, edge_id)
    if not check_result.success:
        return check_result
    
    if not check_result.data:
        return Result.error(f"Edge not found: {edge_id}")
    
    # TODO: In production, should check if edge affects active executions
    
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
    # Validate workflow exists
    if not _validate_workflow_exists(db_path, workflow_id):
        return Result.error(f"Workflow not found: {workflow_id}")
    
    query = "SELECT * FROM edges WHERE workflow_id = ?"
    result = fetch_all(db_path=db_path, query=query, params=(workflow_id,))
    
    if not result.success:
        return Result.error(f"Failed to list workflow edges: {result.error}")
    return Result.success(result.data)

@handle_db_errors("delete workflow edges")
def delete_workflow_edges(db_path, workflow_id):
    # Validate workflow exists
    if not _validate_workflow_exists(db_path, workflow_id):
        return Result.error(f"Workflow not found: {workflow_id}")
    
    # TODO: In production, should check if any edges affect active executions
    
    query = "DELETE FROM edges WHERE workflow_id = ?"
    result = execute_sql_query(
        db_path=db_path, 
        query=query, 
        params=(workflow_id,))

    if not result.success:
        return Result.error(f"Failed to delete workflow edges: {result.error}")
    return Result.success({"deleted": True, "workflow_id": workflow_id})