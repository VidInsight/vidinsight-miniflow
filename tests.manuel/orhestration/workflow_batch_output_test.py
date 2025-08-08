#!/usr/bin/env python3
"""
Workflow batch fonksiyonlarının çıktı formatlarını analiz eder
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from miniflow.database_manager.config import get_sqlite_config
from miniflow.database_manager.engine import DatabaseEngine
from miniflow.database_manager.orchestration import DatabaseOrchestration
from miniflow.database_manager.models import Base, ScriptType
import uuid
import json

def analyze_workflow_batch_outputs():
    """Workflow batch fonksiyonlarının çıktı formatlarını analiz eder"""
    
    print("=" * 80)
    print("WORKFLOW BATCH FUNCTIONS OUTPUT ANALYSIS")
    print("=" * 80)
    
    # Database setup
    config = get_sqlite_config(db_name='test_workflow_batch_output.db')
    engine = DatabaseEngine(config)
    engine.create_tables(Base.metadata)
    orchestration = DatabaseOrchestration()
    
    with engine.get_session_context() as session:
        
        unique_id = uuid.uuid4().hex[:8]
        
        print("\n1. WORKFLOW CREATE OUTPUT ANALYSIS:")
        print("-" * 50)
        
        # Workflow oluştur
        workflow = orchestration.workflow_create(
            session, 
            f'Analysis Workflow {unique_id}',
            'Test workflow for output analysis'
        )
        print(f"Return Type: {type(workflow)}")
        print(f"Return Keys: {list(workflow.keys())}")
        print(f"Full Output: {json.dumps(workflow, indent=2)}")
        workflow_id = workflow['id']
        
        print("\n2. SCRIPT CREATE OUTPUT ANALYSIS:")
        print("-" * 50)
        
        # Script oluştur
        script = orchestration.script_create(session,
            name=f'Analysis Script {unique_id}',
            description='Test script for output analysis',
            language=ScriptType.PYTHON,
            type='python',
            script_path='/path/to/analysis_script.py',
            input_params={'param1': 'string'},
            output_params={'result': 'string'},
            test_status='untested'
        )
        print(f"Return Type: {type(script)}")
        print(f"Return Keys: {list(script.keys())}")
        print(f"Full Output: {json.dumps(script, indent=2)}")
        
        print("\n3. WORKFLOW ADD NODES BATCH OUTPUT ANALYSIS:")
        print("-" * 50)
        
        # Node'ları batch olarak ekle
        nodes_data = [
            {
                'name': 'analysis_node1',
                'script_id': script['id'],
                'params': {'param1': 'value1'},
                'max_retries': 3,
                'timeout_seconds': 300
            },
            {
                'name': 'analysis_node2',
                'script_id': script['id'],
                'params': {'param1': 'value2'},
                'max_retries': 3,
                'timeout_seconds': 300
            }
        ]
        
        added_nodes = orchestration.workflow_add_nodes_batch(session, workflow_id, nodes_data)
        print(f"Return Type: {type(added_nodes)}")
        print(f"List Length: {len(added_nodes)}")
        print(f"First Node Type: {type(added_nodes[0])}")
        print(f"First Node Keys: {list(added_nodes[0].keys())}")
        print(f"Full Output: {json.dumps(added_nodes, indent=2)}")
        
        print("\n4. WORKFLOW ADD EDGES BATCH OUTPUT ANALYSIS:")
        print("-" * 50)
        
        # Edge'leri batch olarak ekle
        edges_data = [
            {
                'from_node_id': added_nodes[0]['id'],
                'to_node_id': added_nodes[1]['id'],
                'condition_type': 'success'
            }
        ]
        
        added_edges = orchestration.workflow_add_edges_batch(session, workflow_id, edges_data)
        print(f"Return Type: {type(added_edges)}")
        print(f"List Length: {len(added_edges)}")
        print(f"First Edge Type: {type(added_edges[0])}")
        print(f"First Edge Keys: {list(added_edges[0].keys())}")
        print(f"Full Output: {json.dumps(added_edges, indent=2)}")
        
        print("\n5. WORKFLOW CLONE OUTPUT ANALYSIS:")
        print("-" * 50)
        
        # Workflow'u klonla
        cloned_workflow = orchestration.workflow_clone(
            session, 
            workflow_id, 
            f'Cloned Analysis Workflow {unique_id}',
            'Cloned workflow for analysis'
        )
        print(f"Return Type: {type(cloned_workflow)}")
        print(f"Return Keys: {list(cloned_workflow.keys())}")
        print(f"Full Output: {json.dumps(cloned_workflow, indent=2)}")
        
        print("\n6. WORKFLOW UPDATE STRUCTURE OUTPUT ANALYSIS:")
        print("-" * 50)
        
        # Yeni workflow oluştur
        update_workflow = orchestration.workflow_create(
            session, 
            f'Update Analysis Workflow {unique_id}',
            'Test workflow for structure update analysis'
        )
        
        # Structure'ı güncelle
        new_nodes = [
            {
                'name': 'updated_analysis_node1',
                'script_id': script['id'],
                'params': {'param1': 'updated_value1'},
                'max_retries': 5,
                'timeout_seconds': 600
            }
        ]
        
        updated_workflow = orchestration.workflow_update_structure(
            session, 
            update_workflow['id'], 
            nodes=new_nodes, 
            edges=None
        )
        print(f"Return Type: {type(updated_workflow)}")
        print(f"Return Keys: {list(updated_workflow.keys())}")
        print(f"Full Output: {json.dumps(updated_workflow, indent=2)}")
        
        print("\n7. NODE AND EDGE CRUD OUTPUT ANALYSIS:")
        print("-" * 50)
        
        # Node CRUD çıktıları
        node_get = orchestration.node_get(session, added_nodes[0]['id'])
        print(f"node_get Return Type: {type(node_get)}")
        print(f"node_get Keys: {list(node_get.keys())}")
        
        node_exists = orchestration.node_exists(session, added_nodes[0]['id'])
        print(f"node_exists Return Type: {type(node_exists)}")
        print(f"node_exists Value: {node_exists}")
        
        node_count = orchestration.node_count(session)
        print(f"node_count Return Type: {type(node_count)}")
        print(f"node_count Value: {node_count}")
        
        node_filter = orchestration.node_filter(session, {'workflow_id': workflow_id})
        print(f"node_filter Return Type: {type(node_filter)}")
        print(f"node_filter Length: {len(node_filter)}")
        
        node_get_by_workflow = orchestration.node_get_by_workflow(session, workflow_id)
        print(f"node_get_by_workflow Return Type: {type(node_get_by_workflow)}")
        print(f"node_get_by_workflow Length: {len(node_get_by_workflow)}")
        
        # Edge CRUD çıktıları
        edge_get = orchestration.edge_get(session, added_edges[0]['id'])
        print(f"edge_get Return Type: {type(edge_get)}")
        print(f"edge_get Keys: {list(edge_get.keys())}")
        
        edge_exists = orchestration.edge_exists(session, added_edges[0]['id'])
        print(f"edge_exists Return Type: {type(edge_exists)}")
        print(f"edge_exists Value: {edge_exists}")
        
        edge_count = orchestration.edge_count(session)
        print(f"edge_count Return Type: {type(edge_count)}")
        print(f"edge_count Value: {edge_count}")
        
        edge_filter = orchestration.edge_filter(session, {'workflow_id': workflow_id})
        print(f"edge_filter Return Type: {type(edge_filter)}")
        print(f"edge_filter Length: {len(edge_filter)}")
        
        edge_get_by_workflow = orchestration.edge_get_by_workflow(session, workflow_id)
        print(f"edge_get_by_workflow Return Type: {type(edge_get_by_workflow)}")
        print(f"edge_get_by_workflow Length: {len(edge_get_by_workflow)}")
        
        print("\n8. SUMMARY OF OUTPUT FORMATS:")
        print("-" * 50)
        print("✅ workflow_create: dict (workflow bilgileri)")
        print("✅ workflow_add_nodes_batch: List[dict] (eklenen node'lar)")
        print("✅ workflow_add_edges_batch: List[dict] (eklenen edge'ler)")
        print("✅ workflow_clone: dict (klonlanan workflow bilgileri)")
        print("✅ workflow_update_structure: dict (güncellenmiş workflow bilgileri)")
        print("✅ node_get: dict (node bilgileri)")
        print("✅ node_exists: bool (varlık kontrolü)")
        print("✅ node_count: int (toplam node sayısı)")
        print("✅ node_filter: List[dict] (filtrelenmiş node'lar)")
        print("✅ node_get_by_workflow: List[dict] (workflow'daki node'lar)")
        print("✅ edge_get: dict (edge bilgileri)")
        print("✅ edge_exists: bool (varlık kontrolü)")
        print("✅ edge_count: int (toplam edge sayısı)")
        print("✅ edge_filter: List[dict] (filtrelenmiş edge'ler)")
        print("✅ edge_get_by_workflow: List[dict] (workflow'daki edge'ler)")

if __name__ == "__main__":
    analyze_workflow_batch_outputs()
