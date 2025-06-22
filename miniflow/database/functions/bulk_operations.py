"""
Bulk Database Operations for Performance Optimization

This module provides bulk database operations to replace sequential 
database queries in batch processing scenarios.
"""

from ..core import handle_db_errors, fetch_all, fetch_one
from ..exceptions import Result
from ..utils import safe_json_loads, safe_json_dumps


@handle_db_errors("bulk get nodes")
def bulk_get_nodes(db_path, node_ids):
    """
    Get multiple nodes in a single query instead of multiple individual queries
    
    Args:
        db_path (str): Database path
        node_ids (list): List of node IDs to fetch
        
    Returns:
        Result: Dictionary of node_id -> node_data mappings
    """
    if not node_ids:
        return Result.success({})
    
    # Create placeholders for parameterized query
    placeholders = ','.join(['?' for _ in node_ids])
    query = f"""
    SELECT id, workflow_id, name, type, script, params
    FROM nodes
    WHERE id IN ({placeholders})
    """
    
    result = fetch_all(db_path=db_path, query=query, params=list(node_ids))
    
    if not result.success:
        return result
    
    # Convert to dict for fast O(1) lookup
    nodes_dict = {}
    for row in result.data:
        nodes_dict[row['id']] = {
            'id': row['id'],
            'workflow_id': row['workflow_id'],
            'name': row['name'],
            'type': row['type'],
            'script': row['script'],
            'params': row['params']
        }
    
    return Result.success(nodes_dict)


@handle_db_errors("bulk get execution results")
def bulk_get_execution_results(db_path, execution_id, node_ids):
    """
    Get multiple execution results in a single query
    
    Args:
        db_path (str): Database path
        execution_id (str): Execution ID
        node_ids (list): List of node IDs to fetch results for
        
    Returns:
        Result: Dictionary of node_id -> result_data mappings
    """
    if not node_ids:
        return Result.success({})
    
    placeholders = ','.join(['?' for _ in node_ids])
    query = f"""
    SELECT node_id, result_data, status, error_message
    FROM execution_results
    WHERE execution_id = ? AND node_id IN ({placeholders})
    """
    
    params = [execution_id] + list(node_ids)
    result = fetch_all(db_path=db_path, query=query, params=params)
    
    if not result.success:
        return result
    
    # Convert to dict for fast lookup
    results_dict = {}
    for row in result.data:
        results_dict[row['node_id']] = {
            'node_id': row['node_id'],
            'result_data': row['result_data'],
            'status': row['status'],
            'error_message': row['error_message']
        }
    
    return Result.success(results_dict)


@handle_db_errors("bulk get workflow nodes mapping")
def bulk_get_workflow_nodes_mapping(db_path, execution_id):
    """
    Get node name to node ID mapping for an execution's workflow
    
    Args:
        db_path (str): Database path
        execution_id (str): Execution ID
        
    Returns:
        Result: Dictionary of node_name -> node_id mappings
    """
    query = """
    SELECT n.name, n.id
    FROM nodes n
    JOIN executions e ON n.workflow_id = e.workflow_id
    WHERE e.id = ?
    """
    
    result = fetch_all(db_path=db_path, query=query, params=(execution_id,))
    
    if not result.success:
        return result
    
    # Create name -> id mapping
    name_to_id = {}
    for row in result.data:
        name_to_id[row['name']] = row['id']
    
    return Result.success(name_to_id)


@handle_db_errors("bulk resolve contexts")
def bulk_resolve_contexts(db_path, execution_id, tasks_with_params):
    """
    Resolve contexts for multiple tasks in bulk
    
    Args:
        db_path (str): Database path
        execution_id (str): Execution ID
        tasks_with_params (list): List of (task, params_dict) tuples
        
    Returns:
        Result: List of resolved contexts
    """
    from ..functions.nodes_table import get_node
    import json
    import re
    
    # Extract all unique dependencies
    all_dependency_node_names = set()
    dependency_mapping = {}  # task_id -> list of (param_name, node_name, attribute)
    
    for task, params_dict in tasks_with_params:
        task_dependencies = []
        
        # Extract dynamic values from params
        for param_name, param_value in params_dict.items():
            if isinstance(param_value, str):
                pattern = r"\{\{(.*?)\}\}"
                matches = re.findall(pattern, param_value)
                for match in matches:
                    if '.' in match:
                        node_name, attribute = match.strip().split('.', 1)
                        all_dependency_node_names.add(node_name)
                        task_dependencies.append((param_name, node_name, attribute))
        
        dependency_mapping[task['id']] = task_dependencies
    
    if not all_dependency_node_names:
        # No dependencies, return original params
        return Result.success([params for _, params in tasks_with_params])
    
    # Bulk get node name -> node id mapping
    mapping_result = bulk_get_workflow_nodes_mapping(db_path, execution_id)
    if not mapping_result.success:
        return mapping_result
    
    name_to_id = mapping_result.data
    
    # Get all dependency node IDs
    dependency_node_ids = []
    for node_name in all_dependency_node_names:
        if node_name in name_to_id:
            dependency_node_ids.append(name_to_id[node_name])
    
    # Bulk get execution results for all dependencies
    if dependency_node_ids:
        results_result = bulk_get_execution_results(db_path, execution_id, dependency_node_ids)
        if not results_result.success:
            return results_result
        results_dict = results_result.data
    else:
        results_dict = {}
    
    # Resolve contexts for all tasks
    resolved_contexts = []
    for task, params_dict in tasks_with_params:
        resolved_params = params_dict.copy()
        
        # Process dependencies for this task
        for param_name, node_name, attribute in dependency_mapping.get(task['id'], []):
            if node_name in name_to_id:
                node_id = name_to_id[node_name]
                if node_id in results_dict:
                    result_data_raw = results_dict[node_id]['result_data']
                    if result_data_raw and results_dict[node_id]['status'] == 'success':
                        try:
                            result_data = safe_json_loads(result_data_raw)
                            if isinstance(result_data, dict) and attribute in result_data:
                                resolved_params[param_name] = result_data[attribute]
                        except:
                            pass  # Keep original value if parsing fails
        
        resolved_contexts.append(resolved_params)
    
    return Result.success(resolved_contexts) 