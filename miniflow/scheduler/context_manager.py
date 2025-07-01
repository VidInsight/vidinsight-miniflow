import re
import json

# Logger setup
import logging
logger = logging.getLogger("miniflow.scheduler.context_manager")

from ..database.core import fetch_one, fetch_all, Result
from ..database.schema import ALL_TABLES

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
    logger.debug(f"Node ID aranıyor - execution_id: {execution_id}, node_name: {node_name}")
    
    # ------------------------------------------------------------
    # 1. Execution ID üzerindne Workflow ID çek
    # ------------------------------------------------------------
    workflow_query = """
    SELECT e.workflow_id 
    FROM executions e
    WHERE e.id = ? AND e.status != 'failed'
    """
    workflow_result = fetch_one(
        db_path=db_path,
        query=workflow_query, 
        params=(execution_id,)
        )
    
    if not workflow_result.success or not workflow_result.data:
        # TODO: Workflow ID bulunamadı hatası
        logger.warning(f"Workflow bulunamadı - execution_id: {execution_id}")
        return None
        
    workflow_id = workflow_result.data.get('workflow_id')
    logger.debug(f"Workflow bulundu - workflow_id: {workflow_id}")
    
    # ------------------------------------------------------------
    # 2. Workfow ID ve Node Name üzerinden Node ID bul
    # ------------------------------------------------------------
    node_query = """
    SELECT n.id 
    FROM nodes n
    WHERE n.workflow_id = ? AND n.name = ?
    """    
    node_result = fetch_one(
        db_path=db_path,
        query=node_query, 
        params=(workflow_id, node_name)
        )
    
    if not node_result.success or not node_result.data:
        # TODO: Noede ID bulunamadı hatası
        logger.warning(f"Node bulunamadı - workflow_id: {workflow_id}, node_name: {node_name}")
        return None
    
    node_id = node_result.data.get('id')
    logger.debug(f"Node bulundu - node_id: {node_id}")
    return node_id

def get_result_data_for_node(db_path, execution_id, node_id):
    logger.debug(f"Result data alınıyor - execution_id: {execution_id}, node_id: {node_id}")

    # ------------------------------------------------------------
    # 1. Execution Results tablosunda ilgili düğümü çek
    # ------------------------------------------------------------
    query = """
    SELECT result_data, status, error_message
    FROM execution_results
    WHERE execution_id = ? AND node_id = ?
    LIMIT 1
    """
    result = fetch_one(
        db_path=db_path,
        query=query, 
        params=(execution_id, node_id)
        )
    
    if not result.success or not result.data:
        # TODO: Hata yönetimi
        logger.debug(f"Result data bulunamadı - execution_id: {execution_id}, node_id: {node_id}")
        return {}
        
    data = result.data
    
    # ------------------------------------------------------------
    # 2. Execution başarılı mı kontrol et
    # ------------------------------------------------------------
    if data.get('status') != 'success':
        error_msg = data.get('error_message', 'Unknown error')
        logger.warning(f"Node execution hatası - node_id: {node_id}, error: {error_msg}")
        return {"error": error_msg}
    
    # ------------------------------------------------------------
    # 3. Result datayı çek
    # ------------------------------------------------------------
    if data.get('result_data'):
        try:
            parsed_data = json.loads(data['result_data'])
            logger.debug(f"Result data parse edildi - node_id: {node_id}")
            return parsed_data
        except json.JSONDecodeError:
            logger.error(f"JSON parse hatası - node_id: {node_id}")
            return {"error": "Invalid JSON"}
    
    logger.debug(f"Boş result data - node_id: {node_id}")
    return {}

def create_context(params_dict, execution_id, db_path):
    logger.debug(f"Context oluşturuluyor - execution_id: {execution_id}")
    
    # Extract dynamic values
    dynamic_values = extract_dynamic_values(params_dict)
    logger.debug(f"Dynamic değerler çıkarıldı: {dynamic_values}")
    
    # Process each dynamic value
    for param_name, path in dynamic_values.items():
        logger.debug(f"Dynamic değer işleniyor - param: {param_name}, path: {path}")
        
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
                    logger.debug(f"Dynamic değer çözümlendi - param: {param_name}, value: {value}")
                else:
                    logger.warning(f"Attribute bulunamadı - param: {param_name}, attribute: {attribute}")
            else:
                logger.warning(f"Result data alınamadı - param: {param_name}, node_id: {node_id}")
        else:
            logger.warning(f"Node ID bulunamadı - param: {param_name}, node_name: {node_name}")
    
    logger.debug(f"Context oluşturuldu - execution_id: {execution_id}")
    return params_dict

def create_context_for_task(params_dict, execution_id, db_path):
    logger.debug(f"Task context oluşturuluyor - execution_id: {execution_id}")
    
    try:
        # If params_dict is already a dict, use it directly
        if isinstance(params_dict, dict):
            params = params_dict
            logger.debug("Params zaten dict formatında")
        else:
            # Try to parse JSON string
            try:
                params = json.loads(params_dict)
                logger.debug("Params JSON string'den parse edildi")
            except json.JSONDecodeError:
                logger.error("Params JSON parse edilemedi")
                return {}
        
        # Process the context
        processed_context = create_context(params, execution_id, db_path)
        
        logger.debug(f"Task context başarıyla oluşturuldu - execution_id: {execution_id}")
        return processed_context
        
    except Exception as e:
        logger.error(f"Task context oluşturma hatası - execution_id: {execution_id}, error: {e}")
        return {}