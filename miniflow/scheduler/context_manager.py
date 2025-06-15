import re
from typing import Dict, Any, Optional

# Database imports
from .. import database


def create_context_for_task(params_dict: Dict[str, Any], execution_id: str, db_path: str) -> Dict[str, Any]:
    """
    Amaç: Task için context oluşturur (execution_results table'dan direkt sorgu ile)
    Döner: İşlenmiş context parametreleri
    
    Bu fonksiyon execution_results tablosundan node sonuçlarını alır ve placeholder'ları replace eder.
    """
    try:
        # Parameters'da placeholder'ları replace et
        processed_context = process_parameters_with_placeholders(params_dict, execution_id, db_path)
        
        return processed_context
        
    except Exception as e:
        # Hata durumunda original params return et
        return params_dict


def get_node_result_data(execution_id: str, node_id: str, db_path: str) -> Dict[str, Any]:
    """
    Amaç: Belirli execution_id ve node_id için result_data'yı alır
    Döner: Parse edilmiş result_data dict'i veya boş dict
    
    execution_results tablosunda: execution_id + node_id -> result_data (JSON)
    """
    try:
        # Direct SQL query to get result_data for specific execution_id + node_id
        from ..database.core import fetch_one
        
        query = """
        SELECT result_data, status
        FROM execution_results 
        WHERE execution_id = ? AND node_id = ? AND status = 'success'
        ORDER BY ended_at DESC
        LIMIT 1
        """
        
        result = fetch_one(db_path=db_path, query=query, params=(execution_id, node_id))
        
        if result.success and result.data:
            result_data = result.data.get('result_data')
            if result_data:
                return database.safe_json_loads(result_data)
        
        return {}
        
    except Exception as e:
        return {}


def process_parameters_with_placeholders(params_dict: Dict[str, Any], execution_id: str, db_path: str) -> Dict[str, Any]:
    """
    Amaç: Parameters'daki {{node_id.variable}} değerlerini replace eder
    Döner: İşlenmiş parameters dict
    
    Her placeholder için execution_results tablosundan ilgili node'un result_data'sını alır.
    """
    try:
        processed = {}
        
        for key, value in params_dict.items():
            if isinstance(value, str) and "{{" in value:
                # Template string'i işle
                processed[key] = replace_placeholder_in_string(value, execution_id, db_path)
            else:
                # Normal value'yu olduğu gibi kopyala
                processed[key] = value
        
        return processed
        
    except Exception as e:
        # Hata durumunda original params return et
        return params_dict


def replace_placeholder_in_string(template_str: str, execution_id: str, db_path: str) -> str:
    """
    Amaç: String'deki {{node_id.variable}} pattern'lerini replace eder
    Döner: İşlenmiş string
    
    Pattern: {{node_id.variable}} -> execution_results table'dan query ile actual value
    """
    try:
        # {{node_id.variable}} pattern'lerini bul
        pattern = r'\{\{([^}]+)\}\}'
        matches = re.findall(pattern, template_str)
        
        result_str = template_str
        
        for match in matches:
            # node_id.variable formatını parse et
            parts = match.strip().split('.')
            
            if len(parts) >= 2:
                node_id = parts[0]
                variable_name = parts[1]
                
                # execution_results tablosundan node result'ını al
                node_result_data = get_node_result_data(execution_id, node_id, db_path)
                
                # Variable value'yu extract et
                if variable_name in node_result_data:
                    value = node_result_data[variable_name]
                    
                    if value is not None:
                        # Placeholder'ı actual value ile replace et
                        result_str = result_str.replace(f"{{{{{match}}}}}", str(value))
        
        return result_str
        
    except Exception as e:
        # Hata durumunda original string return et
        return template_str


def extract_nested_value(data: Dict[str, Any], path: str) -> Any:
    """
    Amaç: Nested dictionary'den path ile değer çıkarır
    Döner: Extracted value veya None
    
    Example: 
    - data = {"user": {"name": "John", "details": {"age": 30}}}
    - path = "user.details.age"
    - return = 30
    """
    try:
        current = data
        path_parts = path.split('.')
        
        for key in path_parts:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
                
        return current
        
    except Exception as e:
        return None


def validate_placeholder_pattern(template_str: str) -> bool:
    """
    Amaç: Template string'deki placeholder pattern'lerinin geçerli olup olmadığını kontrol eder
    Döner: Validation durumu (bool)
    
    Geçerli pattern: {{node_id.variable}} 
    """
    try:
        pattern = r'\{\{([^}]+)\}\}'
        matches = re.findall(pattern, template_str)
        
        for match in matches:
            parts = match.strip().split('.')
            
            # node_id.variable formatı olmalı
            if len(parts) != 2:
                return False
                
            # Node ID ve variable name boş olamaz
            if not parts[0].strip() or not parts[1].strip():
                return False
        
        return True
        
    except Exception as e:
        return False


def replace_placeholders(params_dict: Dict[str, Any], execution_id: str, db_path: str) -> Dict[str, Any]:
    """
    Amaç: Parameters'daki placeholder'ları replace eder (alias for process_parameters_with_placeholders)
    Döner: İşlenmiş parameters dict
    """
    return process_parameters_with_placeholders(params_dict, execution_id, db_path)


def extract_placeholders(params_dict: Dict[str, Any]) -> list:
    """
    Amaç: Parameters'daki placeholder'ları bulur ve listeler
    Döner: Placeholder listesi
    
    Example:
    - params = {"msg": "Hello {{user.name}}", "count": "{{stats.total}}"} 
    - return = ["user.name", "stats.total"]
    """
    try:
        placeholders = []
        pattern = r'\{\{([^}]+)\}\}'
        
        for key, value in params_dict.items():
            if isinstance(value, str):
                matches = re.findall(pattern, value)
                for match in matches:
                    placeholder = match.strip()
                    if placeholder not in placeholders:
                        placeholders.append(placeholder)
        
        return placeholders
        
    except Exception as e:
        return []
