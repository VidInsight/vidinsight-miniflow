import json
import re
import os
from typing import Dict, Any, List, Optional
from datetime import datetime

# Local imports
from ..database import (
    create_workflow, create_node, create_edge, create_trigger,
    delete_workflow, safe_json_dumps, safe_json_loads
)
from .utils.workflow_parser import parse_workflow_json, extract_workflow_metadata


class WorkflowLoader:
    def __init__(self, db_path_or_url: str):
        self.db_path_or_url = db_path_or_url
        self.node_name_to_id_mapping = {}

    def load_workflow_from_file(self, json_file_path: str) -> Dict[str, Any]:
        try:
            if not os.path.exists(json_file_path):
                return self._create_error_result(f"JSON dosyası bulunamadı: {json_file_path}")

            with open(json_file_path, 'r', encoding='utf-8') as f:
                json_content = f.read()

            result = self.load_workflow_from_string(json_content)
            result['source_file'] = json_file_path
            return result

        except Exception as e:
            return self._create_error_result(f"Dosya yükleme hatası: {str(e)}")

    def load_workflow_from_string(self, json_content: str) -> Dict[str, Any]:
        try:
            workflow_data = parse_workflow_json(json_content)
            return self._create_workflow_in_database(workflow_data)
        except Exception as e:
            return self._create_error_result(f"JSON parse hatası: {str(e)}")

    def _create_workflow_in_database(self, workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        workflow_id = None
        created_nodes = []
        created_edges = []
        created_triggers = []

        try:
            workflow_metadata = extract_workflow_metadata(workflow_data)
            created_at_dt = self._parse_datetime_safe(workflow_metadata.get("created_at"))
            updated_at_dt = self._parse_datetime_safe(workflow_metadata.get("updated_at"))

            workflow_result = create_workflow(
                db_path_or_url=self.db_path_or_url,
                name=workflow_metadata["name"],
                description=workflow_metadata.get("description"),
                created_at=created_at_dt,
                updated_at=updated_at_dt
            )

            if not workflow_result.success:
                return self._create_error_result(f"Workflow oluşturulamadı: {workflow_result.error}")

            workflow_id = workflow_result.data["workflow_id"]

            nodes_result = self._create_nodes_with_mapping(workflow_data, workflow_id)
            if not nodes_result['success']:
                raise Exception(nodes_result['error'])

            created_nodes = nodes_result['created_nodes']
            self.node_name_to_id_mapping = nodes_result['name_to_id_mapping']

            params_result = self._update_node_parameters_with_id_mapping()
            if not params_result['success']:
                raise Exception(params_result['error'])

            edges_result = self._create_edges(workflow_data, workflow_id)
            if not edges_result['success']:
                raise Exception(edges_result['error'])

            created_edges = edges_result['created_edges']

            triggers_result = self._create_triggers(workflow_data, workflow_id)
            if not triggers_result['success']:
                raise Exception(triggers_result['error'])

            created_triggers = triggers_result['created_triggers']

            return {
                'success': True,
                'workflow_id': workflow_id,
                'workflow_name': workflow_metadata['name'],
                'nodes_created': len(created_nodes),
                'edges_created': len(created_edges),
                'triggers_created': len(created_triggers),
                'node_mapping': self.node_name_to_id_mapping.copy(),
                'details': {
                    'nodes': created_nodes,
                    'edges': created_edges,
                    'triggers': created_triggers
                }
            }

        except Exception as e:
            if workflow_id:
                try:
                    delete_workflow(self.db_path_or_url, workflow_id)
                except:
                    pass
            return self._create_error_result(f"Workflow oluşturma hatası: {str(e)}")

    def _create_nodes_with_mapping(self, workflow_data: Dict[str, Any], workflow_id: str) -> Dict[str, Any]:
        try:
            steps = workflow_data.get('steps', [])
            created_nodes = []
            name_to_id_mapping = {}

            for step in steps:
                params_dict = step.get('parameters', {})
                params_json = safe_json_dumps(params_dict)

                node_result = create_node(
                    db_path_or_url=self.db_path_or_url,
                    workflow_id=workflow_id,
                    name=step.get('name', ''),
                    type=step.get('type', 'task'),
                    script=step.get('script', ''),
                    params=params_json
                )

                if not node_result.success:
                    raise Exception(f"Node oluşturulamadı ({step.get('name')}): {node_result.error}")

                node_id = node_result.data['node_id']
                node_name = step.get('name', '')

                name_to_id_mapping[node_name] = node_id
                created_nodes.append({
                    'node_id': node_id,
                    'name': node_name,
                    'type': step.get('type', 'task')
                })

            return {
                'success': True,
                'created_nodes': created_nodes,
                'name_to_id_mapping': name_to_id_mapping
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def _update_node_parameters_with_id_mapping(self) -> Dict[str, Any]:
        try:
            from ..database import get_node
            from ..database.functions.nodes_table import update_node_params

            for node_name, node_id in self.node_name_to_id_mapping.items():
                node_result = get_node(self.db_path_or_url, node_id)
                if not node_result.success:
                    continue

                current_params_json = node_result.data.get('params', '{}')
                current_params_dict = safe_json_loads(current_params_json)
                updated_params_dict = self._convert_parameters_name_to_id(current_params_dict)

                update_result = update_node_params(self.db_path_or_url, node_id, updated_params_dict)
                if not update_result.success:
                    raise Exception(f"Node {node_name} parametreleri güncellenemedi: {update_result.error}")

            return {'success': True}

        except Exception as e:
            return {'success': False, 'error': f"Parameter güncelleme hatası: {str(e)}"}

    def _convert_parameters_name_to_id(self, params_dict: Dict[str, Any]) -> Dict[str, Any]:
        try:
            updated_params = {}
            for key, value in params_dict.items():
                if isinstance(value, str):
                    updated_params[key] = self._replace_placeholders_in_string(value)
                elif isinstance(value, dict):
                    updated_params[key] = self._convert_parameters_name_to_id(value)
                elif isinstance(value, list):
                    updated_params[key] = self._convert_parameters_in_list(value)
                else:
                    updated_params[key] = value
            return updated_params
        except Exception:
            return params_dict

    def _replace_placeholders_in_string(self, text: str) -> str:
        try:
            pattern = r'\{\{\s*([^}\s]+)\.([^}\s]+)\s*\}\}'

            def replacement_function(match):
                node_name = match.group(1).strip()
                variable_name = match.group(2).strip()
                if node_name in self.node_name_to_id_mapping:
                    node_id = self.node_name_to_id_mapping[node_name]
                    return f"{{{{ {node_id}.{variable_name} }}}}"
                return match.group(0)

            return re.sub(pattern, replacement_function, text)
        except Exception:
            return text

    def _convert_parameters_in_list(self, param_list: List[Any]) -> List[Any]:
        try:
            updated_list = []
            for item in param_list:
                if isinstance(item, str):
                    updated_list.append(self._replace_placeholders_in_string(item))
                elif isinstance(item, dict):
                    updated_list.append(self._convert_parameters_name_to_id(item))
                elif isinstance(item, list):
                    updated_list.append(self._convert_parameters_in_list(item))
                else:
                    updated_list.append(item)
            return updated_list
        except Exception:
            return param_list

    def _create_edges(self, workflow_data: Dict[str, Any], workflow_id: str) -> Dict[str, Any]:
        try:
            connections = workflow_data.get('connections', [])
            created_edges = []

            for connection in connections:
                from_name = connection.get('from', '')
                to_name = connection.get('to', '')

                if from_name not in self.node_name_to_id_mapping:
                    raise Exception(f"Bilinmeyen source node: {from_name}")
                if to_name not in self.node_name_to_id_mapping:
                    raise Exception(f"Bilinmeyen target node: {to_name}")

                from_node_id = self.node_name_to_id_mapping[from_name]
                to_node_id = self.node_name_to_id_mapping[to_name]

                edge_result = create_edge(
                    db_path_or_url=self.db_path_or_url,
                    workflow_id=workflow_id,
                    from_node_id=from_node_id,
                    to_node_id=to_node_id
                )

                if not edge_result.success:
                    raise Exception(f"Edge oluşturulamadı ({from_name}→{to_name}): {edge_result.error}")

                created_edges.append({
                    'from_node': from_name,
                    'to_node': to_name,
                    'from_node_id': from_node_id,
                    'to_node_id': to_node_id
                })

            return {'success': True, 'created_edges': created_edges}

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _create_triggers(self, workflow_data: Dict[str, Any], workflow_id: str) -> Dict[str, Any]:
        try:
            triggers = workflow_data.get('triggers', [])
            created_triggers = []

            if not triggers:
                created_triggers.append({
                    'type': 'manual',
                    'note': 'Sadece manuel tetikleme'
                })
            else:
                for trigger in triggers:
                    created_triggers.append({
                        'type': 'future_implementation',
                        'note': 'Trigger implementasyonu sonraya bırakıldı'
                    })

            return {'success': True, 'created_triggers': created_triggers}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _create_error_result(self, error_message: str) -> Dict[str, Any]:
        return {
            'success': False,
            'error': error_message,
            'workflow_id': None,
            'nodes_created': 0,
            'edges_created': 0,
            'triggers_created': 0
        }

    def _parse_datetime_safe(self, value):
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except Exception:
                pass
        return None


# Factory functions
def create_workflow_loader(db_path_or_url: str) -> WorkflowLoader:
    return WorkflowLoader(db_path_or_url)

def load_workflow_from_file(db_path_or_url: str, json_file_path: str) -> Dict[str, Any]:
    loader = WorkflowLoader(db_path_or_url)
    return loader.load_workflow_from_file(json_file_path)

def load_workflow_from_json_string(db_path_or_url: str, json_content: str) -> Dict[str, Any]:
    loader = WorkflowLoader(db_path_or_url)
    return loader.load_workflow_from_string(json_content)
