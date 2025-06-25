import json
from typing import Dict, Any, List


class WorkflowParseError(Exception):
    """
    Amaç: Workflow parsing hatalarında kullanılan exception
    """
    pass


class WorkflowValidationError(Exception):
    """
    Amaç: Workflow validation hatalarında kullanılan exception
    """
    pass


def parse_workflow_json(json_content: str) -> Dict[str, Any]:
    """
    Amaç: JSON string'i parse eder ve workflow data'sını döner
    Döner: Parse edilmiş workflow data dict'i
    
    Bu fonksiyon JSON validation yapar ve gerekli alanları kontrol eder
    """
    try:
        workflow_data = json.loads(json_content)
        if not workflow_data:
            raise WorkflowParseError("Invalid JSON content")
        
        _validate_workflow_structure(workflow_data)
        return workflow_data
        
    except json.JSONDecodeError as e:
        raise WorkflowParseError(f"JSON decode error: {str(e)}")
    except Exception as e:
        raise WorkflowParseError(f"Parse error: {str(e)}")


def extract_workflow_metadata(workflow_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Amaç: Workflow'dan metadata bilgilerini çıkarır
    Döner: Metadata dict'i (name, description, version)
    """
    try:
        metadata = {
            'name': workflow_data.get('name', ''),
            'description': workflow_data.get('description', ''),
            'version': workflow_data.get('version', '1.0')
        }
        return metadata
        
    except Exception as e:
        raise WorkflowParseError(f"Metadata extraction error: {str(e)}")


def extract_nodes(workflow_data: Dict[str, Any], workflow_id: str) -> List[Dict[str, Any]]:
    """
    Amaç: Workflow'dan node bilgilerini çıkarır
    Döner: Node listesi
    """
    try:
        nodes = []
        steps = workflow_data.get('steps', [])
        
        for step in steps:
            node = {
                'workflow_id': workflow_id,
                'name': step.get('name', ''),
                'type': step.get('type', 'task'),
                'script': step.get('script', ''),
                'params': step.get('parameters', {})
            }
            nodes.append(node)
            
        return nodes
        
    except Exception as e:
        raise WorkflowParseError(f"Node extraction error: {str(e)}")


def extract_edges(workflow_data: Dict[str, Any], workflow_id: str, node_mapping: Dict[str, str]) -> List[Dict[str, Any]]:
    """
    Amaç: Workflow'dan edge bilgilerini çıkarır
    Döner: Edge listesi
    """
    try:
        edges = []
        connections = workflow_data.get('connections', [])
        
        for connection in connections:
            from_name = connection.get('from', '')
            to_name = connection.get('to', '')
            
            if from_name not in node_mapping or to_name not in node_mapping:
                raise WorkflowValidationError(f"Invalid connection: {from_name} -> {to_name}")
            
            edge = {
                'workflow_id': workflow_id,
                'from_node_id': node_mapping[from_name],
                'to_node_id': node_mapping[to_name],
                'condition_type': connection.get('condition_type', 'success')
            }
            edges.append(edge)
            
        return edges
        
    except Exception as e:
        raise WorkflowParseError(f"Edge extraction error: {str(e)}")


def extract_triggers(workflow_data: Dict[str, Any], workflow_id: str) -> List[Dict[str, Any]]:
    """
    Amaç: Workflow'dan trigger bilgilerini çıkarır
    Döner: Trigger listesi
    """
    try:
        triggers = []
        trigger_configs = workflow_data.get('triggers', [])
        
        for trigger_config in trigger_configs:
            trigger = {
                'workflow_id': workflow_id,
                'trigger_type': trigger_config.get('type', 'manual'),
                'config': trigger_config.get('config', {})
            }
            triggers.append(trigger)
            
        return triggers
        
    except Exception as e:
        raise WorkflowParseError(f"Trigger extraction error: {str(e)}")


def _validate_workflow_structure(workflow_data: Dict[str, Any]) -> None:
    """
    Amaç: Workflow JSON yapısını validate eder
    Döner: Yok (exception fırlatır hata durumunda)
    
    Kontrol edilen alanlar:
    - name (zorunlu)
    - steps (zorunlu, array olmalı, en az 1 tane)
    - her step'in name'i olmalı ve unique olmalı
    - connection'lar geçerli step name'leri referans etmeli
    """
    # Required fields kontrolü
    required_fields = ['name', 'steps']
    for field in required_fields:
        if field not in workflow_data:
            raise WorkflowValidationError(f"Missing required field: {field}")
    
    # Steps array kontrolü
    if not isinstance(workflow_data['steps'], list):
        raise WorkflowValidationError("Steps must be a list")
    
    if len(workflow_data['steps']) == 0:
        raise WorkflowValidationError("Workflow must have at least one step")
    
    # Step validation
    step_names = []
    for step in workflow_data['steps']:
        if not isinstance(step, dict):
            raise WorkflowValidationError("Each step must be a dictionary")
        
        if 'name' not in step:
            raise WorkflowValidationError("Each step must have a name")
        
        step_name = step['name']
        if step_name in step_names:
            raise WorkflowValidationError(f"Duplicate step name: {step_name}")
        
        step_names.append(step_name)
        
        # Step type kontrolü
        if 'type' not in step:
            raise WorkflowValidationError(f"Step '{step_name}' must have a type")
        
        # Script kontrolü
        if 'script' not in step:
            raise WorkflowValidationError(f"Step '{step_name}' must have a script")
    
    # Connection validation
    connections = workflow_data.get('connections', [])
    for connection in connections:
        if not isinstance(connection, dict):
            raise WorkflowValidationError("Each connection must be a dictionary")
        
        if 'from' not in connection or 'to' not in connection:
            raise WorkflowValidationError("Each connection must have 'from' and 'to' fields")
        
        if connection['from'] not in step_names:
            raise WorkflowValidationError(f"Connection references unknown step: {connection['from']}")
        
        if connection['to'] not in step_names:
            raise WorkflowValidationError(f"Connection references unknown step: {connection['to']}")
        
        # Self-reference kontrolü
        if connection['from'] == connection['to']:
            raise WorkflowValidationError(f"Step cannot connect to itself: {connection['from']}")


def validate_workflow_example(workflow_data: Dict[str, Any]) -> bool:
    """
    Amaç: Workflow'un example JSON formatına uygun olup olmadığını kontrol eder
    Döner: Validation durumu (True/False)
    
    Bu fonksiyon user'ın verdiği example format'a göre özel validation yapar
    """
    try:
        _validate_workflow_structure(workflow_data)
        
        # Additional validation for the example format
        if 'version' not in workflow_data:
            raise WorkflowValidationError("Workflow should have a version field")
        
        if 'description' not in workflow_data:
            raise WorkflowValidationError("Workflow should have a description field")
        
        # Parameter format kontrolü
        for step in workflow_data.get('steps', []):
            if 'parameters' in step:
                parameters = step['parameters']
                if not isinstance(parameters, dict):
                    raise WorkflowValidationError(f"Parameters for step '{step['name']}' must be a dictionary")
        
        return True
        
    except (WorkflowValidationError, WorkflowParseError):
        return False 