from ..core import execute_sql_query, fetch_all, fetch_one, handle_db_errors
from ..utils import generate_uuid, safe_json_dumps, generate_timestamp, safe_json_loads
from ..exceptions import Result


# Temel CRUD operasyonaları
@handle_db_errors("create record")
def create_record(db_path, execution_id, node_id, status, result_data=None, error_message=None, started_at=None, ended_at=None):
    """
    Creates an execution result record with standardized status values:
    - 'running': Node is currently executing
    - 'success': Node completed successfully
    - 'failed': Node execution failed
    - 'cancelled': Node execution was cancelled
    """
    record_id = generate_uuid()
    
    # Set timestamps if not provided - only set started_at for all statuses
    if started_at is None:
        started_at = generate_timestamp()
    
    # Set ended_at only for final statuses (success, failed, cancelled)
    if ended_at is None and status in ['success', 'failed', 'cancelled']:
        ended_at = generate_timestamp()
    
    query = """
    INSERT INTO execution_results (id, execution_id, node_id, status, result_data, error_message, started_at, ended_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """
    
    result = execute_sql_query(
        db_path=db_path,
        query=query,
        params=(record_id, execution_id, node_id, status, safe_json_dumps(result_data), error_message, started_at, ended_at)
    )
    
    if not result.success:
        return Result.error(f"Failed to create execution result record: {result.error}")
    return Result.success({"record_id": record_id})

@handle_db_errors("find record")
def find_record(db_path, record_id):
    query = "SELECT * FROM execution_results WHERE id = ?"
    result = fetch_one(db_path=db_path, query=query, params=(record_id,))
    
    if not result.success:
        return Result.error(f"Failed to find execution result record: {result.error}")
    return Result.success(result.data)

@handle_db_errors("delete record")
def delete_record(db_path, record_id):
    query = "DELETE FROM execution_results WHERE id = ?"
    result = execute_sql_query(db_path=db_path, query=query, params=(record_id,))
    
    if not result.success:
        return Result.error(f"Failed to delete execution result record: {result.error}")
    return Result.success({"deleted": True, "record_id": record_id})


# Executions tablosu ile bağlantılı işlemler
@handle_db_errors("list execution records")
def list_execution_records(db_path, execution_id):
    query = """
    SELECT er.*, n.name as node_name, n.type as node_type 
    FROM execution_results er
    JOIN nodes n ON er.node_id = n.id
    WHERE er.execution_id = ?
    ORDER BY er.started_at ASC
    """
    result = fetch_all(db_path=db_path, query=query, params=(execution_id,))
    
    if not result.success:
        return Result.error(f"Failed to list execution records: {result.error}")
    return Result.success(result.data)

@handle_db_errors("delete execution records")
def delete_execution_records(db_path, execution_id):
    query = "DELETE FROM execution_results WHERE execution_id = ?"
    result = execute_sql_query(db_path=db_path, query=query, params=(execution_id,))
    
    if not result.success:
        return Result.error(f"Failed to delete execution records: {result.error}")
    return Result.success({"deleted": True, "execution_id": execution_id, "affected_rows": result.data.get("affected_rows", 0)})

@handle_db_errors("combine execution records results")
def combine_execution_records_results(db_path, execution_id):
    """
    Combines execution results into a consistent format.
    Returns a dictionary where each node_id maps to a standardized result object:
    {
        "node_id": {
            "status": "success|failed|cancelled|skipped",
            "result": <actual_result_data_or_null>,
            "error": <error_message_or_null>,
            "timestamp": <completion_timestamp_or_null>
        }
    }
    """
    # Get all execution records
    records_result = list_execution_records(db_path, execution_id)
    if not records_result.success:
        return records_result
    
    # Get all nodes for this execution to identify skipped ones
    workflow_query = """
    SELECT n.id as node_id 
    FROM nodes n 
    JOIN executions e ON n.workflow_id = e.workflow_id 
    WHERE e.id = ?
    """
    nodes_result = fetch_all(db_path=db_path, query=workflow_query, params=(execution_id,))
    if not nodes_result.success:
        return Result.error(f"Failed to get workflow nodes: {nodes_result.error}")
    
    # Create combined results dictionary with consistent structure
    combined_results = {}
    executed_nodes = set()
    
    # Process executed nodes
    for record in records_result.data:
        node_id = record["node_id"]
        executed_nodes.add(node_id)
        
        # Create standardized result structure
        node_result = {
            "status": record["status"],
            "result": None,
            "error": None,
            "timestamp": record.get("ended_at") or record.get("started_at")
        }
        
        if record["status"] == "failed":
            node_result["error"] = record["error_message"] or "Unknown error"
        elif record["status"] == "success":
            # Parse result_data back to original format
            result_data = record["result_data"]
            if result_data:
                node_result["result"] = safe_json_loads(result_data)
            else:
                node_result["result"] = None
        # For other statuses (running, cancelled), keep result and error as None
        
        combined_results[node_id] = node_result
    
    # Mark non-executed nodes as SKIPPED
    for node in nodes_result.data:
        node_id = node["node_id"]
        if node_id not in executed_nodes:
            combined_results[node_id] = {
                "status": "skipped",
                "result": None,
                "error": None,
                "timestamp": None
            }
    
    return Result.success(combined_results)

@handle_db_errors("get record status")
def get_record_status(db_path, record_id):
    query = "SELECT status, started_at, ended_at FROM execution_results WHERE id = ?"
    result = fetch_one(db_path=db_path, query=query, params=(record_id,))
    
    if not result.success:
        return Result.error(f"Failed to get record status: {result.error}")
    
    if not result.data:
        return Result.error(f"Record not found: {record_id}")
    
    return Result.success({
        "status": result.data["status"],
        "started_at": result.data["started_at"], 
        "ended_at": result.data["ended_at"]
    })

@handle_db_errors("get record timestamp")
def get_record_timestamp(db_path, record_id):
    query = "SELECT started_at, ended_at FROM execution_results WHERE id = ?"
    result = fetch_one(db_path=db_path, query=query, params=(record_id,))
    
    if not result.success:
        return Result.error(f"Failed to get record timestamp: {result.error}")
    
    if not result.data:
        return Result.error(f"Record not found: {record_id}")
    
    return Result.success({
        "started_at": result.data["started_at"],
        "ended_at": result.data["ended_at"]
    })