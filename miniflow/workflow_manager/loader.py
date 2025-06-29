import json
import re
import os
from typing import Dict, Any, List, Optional

# Local imports
from ..database import (
    create_workflow, create_node, create_edge, create_trigger,
    delete_workflow, safe_json_dumps, safe_json_loads
)
from .utils.workflow_parser import parse_workflow_json, extract_workflow_metadata


class WorkflowLoader:
    """
    Amaç: JSON workflow dosyalarını okur ve database'e yükler
    
    Kritik Özellik: node_name.variable → node_id.variable dönüşümü
    Kullanıcı {{ step1.output }} yazar, sistem {{ node_id_123.output }} olarak günceller
    """
    
    def __init__(self, db_path: str):
        """
        Amaç: WorkflowLoader'ı başlatır
        Döner: Yok (constructor)
        """
        self.db_path = db_path
        self.node_name_to_id_mapping = {}  # step_name -> node_id mapping
        
    def load_workflow_from_file(self, json_file_path: str) -> Dict[str, Any]:
        """
        Amaç: JSON dosyasından workflow yükler (ana fonksiyon)
        Döner: Yükleme sonucu ve detayları
        
        Bu fonksiyon tüm workflow yükleme sürecini koordine eder:
        1. JSON validation
        2. Workflow creation  
        3. Node creation + name mapping
        4. Parameter processing (name → id conversion)
        5. Edge creation
        6. Trigger creation
        """
        try:
            # JSON dosyasını oku
            if not os.path.exists(json_file_path):
                return self._create_error_result(f"JSON dosyası bulunamadı: {json_file_path}")
            
            with open(json_file_path, 'r', encoding='utf-8') as f:
                json_content = f.read()
            
            # Workflow'u yükle
            result = self.load_workflow_from_string(json_content)
            result['source_file'] = json_file_path
            
            return result
            
        except Exception as e:
            return self._create_error_result(f"Dosya yükleme hatası: {str(e)}")
    
    def load_workflow_from_string(self, json_content: str) -> Dict[str, Any]:
        """
        Amaç: JSON string'den workflow yükler
        Döner: Yükleme sonucu ve detayları
        """
        try:
            # JSON'u parse et ve validate et
            workflow_data = parse_workflow_json(json_content)
            
            # Workflow'u database'e yükle
            return self._create_workflow_in_database(workflow_data)
            
        except Exception as e:
            return self._create_error_result(f"JSON parse hatası: {str(e)}")
    
    def _create_workflow_in_database(self, workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Amaç: Workflow'u database'e oluşturur (transaction mantığı ile)
        Döner: Oluşturma sonucu
        """
        workflow_id = None
        created_nodes = []
        created_edges = []
        created_triggers = []
        
        try:
            # 1. Workflow oluştur
            workflow_metadata = extract_workflow_metadata(workflow_data)
            workflow_result = create_workflow(
                db_path=self.db_path,
                name=workflow_metadata['name'],
                description=workflow_metadata['description']
            )
            
            if not workflow_result.success:
                return self._create_error_result(f"Workflow oluşturulamadı: {workflow_result.error}")
            
            workflow_id = workflow_result.data['workflow_id']
            
            # 2. Node'ları oluştur ve name mapping topla
            nodes_result = self._create_nodes_with_mapping(workflow_data, workflow_id)
            if not nodes_result['success']:
                raise Exception(nodes_result['error'])
            
            created_nodes = nodes_result['created_nodes']
            self.node_name_to_id_mapping = nodes_result['name_to_id_mapping']
            
            # 3. CRITICAL: Node parametrelerini güncelle (name → id conversion)
            params_result = self._update_node_parameters_with_id_mapping()
            if not params_result['success']:
                raise Exception(params_result['error'])
            
            # 4. Edge'leri oluştur
            edges_result = self._create_edges(workflow_data, workflow_id)
            if not edges_result['success']:
                raise Exception(edges_result['error'])
            
            created_edges = edges_result['created_edges']
            
            # 5. Trigger'ları oluştur (eğer varsa)
            triggers_result = self._create_triggers(workflow_data, workflow_id)
            if not triggers_result['success']:
                raise Exception(triggers_result['error'])
            
            created_triggers = triggers_result['created_triggers']
            
            # Başarılı sonuç
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
            # Rollback: Workflow'u sil (cascade delete ile ilgili veriler de silinir)
            if workflow_id:
                try:
                    delete_workflow(self.db_path, workflow_id)
                except:
                    pass  # Rollback hatalarını görmezden gel
            
            return self._create_error_result(f"Workflow oluşturma hatası: {str(e)}")
    
    def _create_nodes_with_mapping(self, workflow_data: Dict[str, Any], workflow_id: str) -> Dict[str, Any]:
        """
        Amaç: Node'ları oluşturur ve name→id mapping'i toplar
        Döner: Oluşturma sonucu ve mapping
        """
        try:
            steps = workflow_data.get('steps', [])
            created_nodes = []
            name_to_id_mapping = {}
            
            for step in steps:
                # Node parametrelerini JSON string olarak hazırla
                params_dict = step.get('parameters', {})
                params_json = safe_json_dumps(params_dict)
                
                # Node'u oluştur
                node_result = create_node(
                    db_path=self.db_path,
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
                
                # Mapping'e ekle
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
        """
        Amaç: CRITICAL FUNCTION - Node parametrelerini günceller (name → id conversion)
        Döner: Güncelleme sonucu
        
        Bu fonksiyon {{ step1.output }} → {{ node_id_123.output }} dönüşümünü yapar
        """
        try:
            from ..database import get_node, safe_json_loads
            from ..database.functions.nodes_table import update_node_params
            
            for node_name, node_id in self.node_name_to_id_mapping.items():
                # Node'un current parametrelerini al
                node_result = get_node(self.db_path, node_id)
                if not node_result.success:
                    continue
                
                current_params_json = node_result.data.get('params', '{}')
                current_params_dict = safe_json_loads(current_params_json)
                
                # Parametrelerde name → id conversion yap
                updated_params_dict = self._convert_parameters_name_to_id(current_params_dict)
                
                # Güncellenmiş parametreleri JSON'a çevir
                updated_params_json = safe_json_dumps(updated_params_dict)
                
                # Node parametrelerini güncelle (string olarak değil dict olarak)
                update_result = update_node_params(self.db_path, node_id, updated_params_dict)
                if not update_result.success:
                    raise Exception(f"Node {node_name} parametreleri güncellenemedi: {update_result.error}")
            
            return {'success': True}
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Parameter güncelleme hatası: {str(e)}"
            }
    
    def _convert_parameters_name_to_id(self, params_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Amaç: Parameter dict'indeki {{ node_name.variable }} → {{ node_id.variable }} dönüşümü
        Döner: Güncellenmiş parameter dict
        
        Example:
        Input:  {"input_data": "{{ step1.output_data }}"}
        Output: {"input_data": "{{ node_id_123.output_data }}"}
        """
        try:
            updated_params = {}
            
            for key, value in params_dict.items():
                if isinstance(value, str):
                    # String değerlerde placeholder conversion yap
                    updated_value = self._replace_placeholders_in_string(value)
                    updated_params[key] = updated_value
                elif isinstance(value, dict):
                    # Nested dict için recursive call
                    updated_params[key] = self._convert_parameters_name_to_id(value)
                elif isinstance(value, list):
                    # List içindeki string'leri kontrol et
                    updated_params[key] = self._convert_parameters_in_list(value)
                else:
                    # Diğer veri tipleri (int, bool, etc.) olduğu gibi kopyala
                    updated_params[key] = value
            
            return updated_params
            
        except Exception as e:
            # Hata durumunda original params'ı döndür
            return params_dict
    
    def _replace_placeholders_in_string(self, text: str) -> str:
        """
        Amaç: String'deki {{ node_name.variable }} placeholder'larını {{ node_id.variable }} ile değiştirir
        Döner: Güncellenmiş string
        """
        try:
            # Pattern: {{ node_name.variable_name }}
            pattern = r'\{\{\s*([^}\s]+)\.([^}\s]+)\s*\}\}'
            
            def replacement_function(match):
                node_name = match.group(1).strip()
                variable_name = match.group(2).strip()
                
                # Node name'i node ID'ye çevir
                if node_name in self.node_name_to_id_mapping:
                    node_id = self.node_name_to_id_mapping[node_name]
                    return f"{{{{ {node_id}.{variable_name} }}}}"
                else:
                    # Mapping'de bulunamayan node name'leri olduğu gibi bırak
                    return match.group(0)
            
            # Tüm placeholder'ları değiştir
            updated_text = re.sub(pattern, replacement_function, text)
            return updated_text
            
        except Exception as e:
            # Hata durumunda original text'i döndür
            return text
    
    def _convert_parameters_in_list(self, param_list: List[Any]) -> List[Any]:
        """
        Amaç: List içindeki parametrelerde conversion yapar
        Döner: Güncellenmiş list
        """
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
            
        except Exception as e:
            return param_list
    
    def _create_edges(self, workflow_data: Dict[str, Any], workflow_id: str) -> Dict[str, Any]:
        """
        Amaç: Workflow connection'larını edge olarak oluşturur
        Döner: Oluşturma sonucu
        """
        try:
            connections = workflow_data.get('connections', [])
            created_edges = []
            
            for connection in connections:
                from_name = connection.get('from', '')
                to_name = connection.get('to', '')
                
                # Node name'lerini ID'lere çevir
                if from_name not in self.node_name_to_id_mapping:
                    raise Exception(f"Bilinmeyen source node: {from_name}")
                
                if to_name not in self.node_name_to_id_mapping:
                    raise Exception(f"Bilinmeyen target node: {to_name}")
                
                from_node_id = self.node_name_to_id_mapping[from_name]
                to_node_id = self.node_name_to_id_mapping[to_name]
                
                # Edge oluştur
                edge_result = create_edge(
                    db_path=self.db_path,
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
            
            return {
                'success': True,
                'created_edges': created_edges
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _create_triggers(self, workflow_data: Dict[str, Any], workflow_id: str) -> Dict[str, Any]:
        """
        Amaç: Workflow trigger'larını oluşturur
        Döner: Oluşturma sonucu
        """
        try:
            triggers = workflow_data.get('triggers', [])
            created_triggers = []
            
            # Trigger array'i boşsa manuel trigger demektir
            if not triggers:
                created_triggers.append({
                    'type': 'manual',
                    'note': 'Sadece manuel tetikleme'
                })
            else:
                # Gelecekte trigger implementasyonu burada yapılacak
                for trigger in triggers:
                    created_triggers.append({
                        'type': 'future_implementation',
                        'note': 'Trigger implementasyonu sonraya bırakıldı'
                    })
            
            return {
                'success': True,
                'created_triggers': created_triggers
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _create_error_result(self, error_message: str) -> Dict[str, Any]:
        """
        Amaç: Standart error result formatı oluşturur
        Döner: Error result dict
        """
        return {
            'success': False,
            'error': error_message,
            'workflow_id': None,
            'nodes_created': 0,
            'edges_created': 0,
            'triggers_created': 0
        }


# Factory functions
def create_workflow_loader(db_path: str) -> WorkflowLoader:
    """
    Amaç: WorkflowLoader factory function
    Döner: WorkflowLoader instance
    """
    return WorkflowLoader(db_path)


def load_workflow_from_file(db_path: str, json_file_path: str) -> Dict[str, Any]:
    """
    Amaç: Tek seferlik workflow yükleme (convenience function)
    Döner: Yükleme sonucu
    """
    loader = WorkflowLoader(db_path)
    return loader.load_workflow_from_file(json_file_path)


def load_workflow_from_json_string(db_path: str, json_content: str) -> Dict[str, Any]:
    """
    Amaç: JSON string'den tek seferlik workflow yükleme
    Döner: Yükleme sonucu
    """
    loader = WorkflowLoader(db_path)
    return loader.load_workflow_from_string(json_content)
