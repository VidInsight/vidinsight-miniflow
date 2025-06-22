import re
import json
from ..database.core import fetch_one, fetch_all, Result
from ..database.schema import ALL_TABLES
from ..utils.logger import logger

def extract_dynamic_values(params):
    pattern = r"\{\{(.*?)\}\}"
    extracted = {}

    for key, value in params.items():
        if isinstance(value, str):
            match = re.search(pattern, value)
            if match:
                extracted[key] = match.group(1).strip()
    return extracted

def split_variable_path(path: str):
    parts = path.strip().split('.', 1)
    if len(parts) == 2:
        return parts[0], parts[1]
    return parts[0], None

def find_node_id(db_path, execution_id, node_name):
    """
    Find node_id for a given execution_id and node_name.
    First gets workflow_id from executions table, then finds node_id from nodes table.
    
    Args:
        db_path (str): Database path
        execution_id (str): Execution ID
        node_name (str): Node name
        
    Returns:
        str: Node ID if found, None otherwise
    """
    # First get workflow_id from executions table using index
    workflow_query = """
    SELECT e.workflow_id 
    FROM executions e
    WHERE e.id = ? AND e.status != 'failed'
    """
    workflow_result = fetch_one(db_path=db_path,
                              query=workflow_query, 
                              params=(execution_id,))
    
    if not workflow_result.success or not workflow_result.data:
        return None
        
    workflow_id = workflow_result.data.get('workflow_id')
    
    # Then find node_id from nodes table using index
    node_query = """
    SELECT n.id 
    FROM nodes n
    WHERE n.workflow_id = ? AND n.name = ?
    """    
    node_result = fetch_one(db_path=db_path,
                          query=node_query, 
                          params=(workflow_id, node_name))
    
    if not node_result.success or not node_result.data:
        return None
        
    node_id = node_result.data.get('id')
    return node_id

def get_result_data_for_node(db_path, execution_id, node_id):
    """
    Get result data for a node from execution_results table.
    
    Args:
        db_path (str): Database path
        execution_id (str): Execution ID
        node_id (str): Node ID
        
    Returns:
        dict: Result data if successful, empty dict otherwise
    """
    query = """
    SELECT result_data, status, error_message
    FROM execution_results
    WHERE execution_id = ? AND node_id = ?
    LIMIT 1
    """
    result = fetch_one(db_path=db_path,
                      query=query, 
                      params=(execution_id, node_id))
    
    if not result.success or not result.data:
        return {}
        
    data = result.data
    
    # Check if the execution was successful
    if data.get('status') != 'success':
        error_msg = data.get('error_message', 'Unknown error')
        return {"error": error_msg}
    
    if data.get('result_data'):
        try:
            parsed_data = json.loads(data['result_data'])
            return parsed_data
        except json.JSONDecodeError:
            return {"error": "Invalid JSON"}
    
    return {}

def create_context(params_dict, execution_id, db_path):
    """
    Create context for a task by resolving dynamic values.
    
    Args:
        params_dict (dict): Task parameters
        execution_id (str): Execution ID
        db_path (str): Database path
        
    Returns:
        dict: Processed context with resolved values
    """
    # Extract dynamic values
    dynamic_values = extract_dynamic_values(params_dict)
    
    # Process each dynamic value
    for param_name, path in dynamic_values.items():
        # Split path into node name and attribute
        node_name, attribute = split_variable_path(path)
        
        # Find node_id for the node name
        node_id = find_node_id(db_path, execution_id, node_name)
        
        if node_id:
            # Get result data for the node
            result_data = get_result_data_for_node(db_path, execution_id, node_id)
            
            if result_data and isinstance(result_data, dict):
                # Get the attribute value
                value = result_data.get(attribute)
                
                if value is not None:
                    # Replace the placeholder with the actual value
                    params_dict[param_name] = value
    
    return params_dict

def create_context_for_task(params_dict, execution_id, db_path):
    """
    Creates context for a task by processing the parameters and resolving dynamic values.
    
    Args:
        params_dict (str): JSON string containing the parameters
        execution_id (str): The execution ID
        db_path (str): Path to the database
        
    Returns:
        dict: Processed context with resolved dynamic values
    """
    try:
        # If params_dict is already a dict, use it directly
        if isinstance(params_dict, dict):
            params = params_dict
        else:
            # Try to parse JSON string
            try:
                params = json.loads(params_dict)
            except json.JSONDecodeError:
                return {}
        
        # Process the context
        processed_context = create_context(params, execution_id, db_path)
        
        return processed_context
        
    except Exception:
        return {}

def get_table_info(db_path, table_name):
    """
    Get table information with SQL injection protection.
    
    Args:
        db_path (str): Database path
        table_name (str): Name of the table to get info for
        
    Returns:
        Result: Success with table info or error
    """
    try:
        # Validate table name against known tables
        valid_tables = [table_name for table_name, _ in ALL_TABLES]
        if table_name not in valid_tables:
            return Result.error(f"Invalid table name: {table_name}")
        
        # Safe to use f-string now since we validated the table name
        result = fetch_all(db_path, f"PRAGMA table_info({table_name})")
        
        if not result.success:
            return result
        
        columns = []
        for row in result.data:
            columns.append({
                "name": row["name"],
                "type": row["type"],
                "not_null": bool(row["notnull"]),
                "default_value": row["dflt_value"],
                "primary_key": bool(row["pk"])
            })
        
        return Result.success({
            "table_name": table_name,
            "columns": columns,
            "column_count": len(columns)
        })
     
    except Exception as e:
        return Result.error(f"Failed to get table info for {table_name}: {str(e)}")
