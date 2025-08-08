#!/usr/bin/env python3
"""
Workflow batch fonksiyonlarını test eder
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from miniflow.database_manager.config import get_sqlite_config
from miniflow.database_manager.engine import DatabaseEngine
from miniflow.database_manager.orchestration import DatabaseOrchestration
from miniflow.database_manager.models import Base, ScriptType
import uuid

def test_workflow_batch_operations():
    """Workflow batch fonksiyonlarını test eder"""
    
    print("=" * 60)
    print("WORKFLOW BATCH OPERATIONS TEST")
    print("=" * 60)
    
    # Database setup
    config = get_sqlite_config(db_name='test_workflow_batch.db')
    engine = DatabaseEngine(config)
    engine.create_tables(Base.metadata)
    orchestration = DatabaseOrchestration()
    
    with engine.get_session_context() as session:
        
        unique_id = uuid.uuid4().hex[:8]
        
        print("\n1. WORKFLOW CREATE TEST:")
        print("-" * 30)
        
        # Workflow oluştur
        workflow = orchestration.workflow_create(
            session, 
            f'Test Workflow {unique_id}',
            'Test workflow for batch operations'
        )
        print(f"Workflow Created: {workflow['id']}")
        workflow_id = workflow['id']
        
        print("\n2. SCRIPT CREATE TEST:")
        print("-" * 30)
        
        # Script'ler oluştur
        script1 = orchestration.script_create(session,
            name=f'Script 1 {unique_id}',
            description='First script',
            language=ScriptType.PYTHON,
            type='python',
            script_path='/path/to/script1.py',
            input_params={'param1': 'string'},
            output_params={'result': 'string'},
            test_status='untested'
        )
        
        script2 = orchestration.script_create(session,
            name=f'Script 2 {unique_id}',
            description='Second script',
            language=ScriptType.PYTHON,
            type='python',
            script_path='/path/to/script2.py',
            input_params={'param1': 'string'},
            output_params={'result': 'string'},
            test_status='untested'
        )
        
        script3 = orchestration.script_create(session,
            name=f'Script 3 {unique_id}',
            description='Third script',
            language=ScriptType.PYTHON,
            type='python',
            script_path='/path/to/script3.py',
            input_params={'param1': 'string'},
            output_params={'result': 'string'},
            test_status='untested'
        )
        
        print(f"Scripts Created: {script1['id']}, {script2['id']}, {script3['id']}")
        
        print("\n3. WORKFLOW ADD NODES BATCH TEST:")
        print("-" * 30)
        
        # Node'ları batch olarak ekle
        nodes_data = [
            {
                'name': 'node1',
                'script_id': script1['id'],
                'params': {'param1': 'value1'},
                'max_retries': 3,
                'timeout_seconds': 300
            },
            {
                'name': 'node2',
                'script_id': script2['id'],
                'params': {'param1': 'value2'},
                'max_retries': 3,
                'timeout_seconds': 300
            },
            {
                'name': 'node3',
                'script_id': script3['id'],
                'params': {'param1': 'value3'},
                'max_retries': 3,
                'timeout_seconds': 300
            }
        ]
        
        added_nodes = orchestration.workflow_add_nodes_batch(session, workflow_id, nodes_data)
        print(f"Added {len(added_nodes)} nodes:")
        for node in added_nodes:
            print(f"  - {node['name']}: {node['id']}")
        
        print("\n4. WORKFLOW ADD EDGES BATCH TEST:")
        print("-" * 30)
        
        # Edge'leri batch olarak ekle
        edges_data = [
            {
                'from_node_id': added_nodes[0]['id'],
                'to_node_id': added_nodes[1]['id'],
                'condition_type': 'success'
            },
            {
                'from_node_id': added_nodes[1]['id'],
                'to_node_id': added_nodes[2]['id'],
                'condition_type': 'success'
            }
        ]
        
        added_edges = orchestration.workflow_add_edges_batch(session, workflow_id, edges_data)
        print(f"Added {len(added_edges)} edges:")
        for edge in added_edges:
            print(f"  - {edge['from_node_id']} -> {edge['to_node_id']}: {edge['condition_type']}")
        
        print("\n5. WORKFLOW CLONE TEST:")
        print("-" * 30)
        
        # Workflow'u klonla
        cloned_workflow = orchestration.workflow_clone(
            session, 
            workflow_id, 
            f'Cloned Workflow {unique_id}',
            'Cloned workflow description'
        )
        print(f"Cloned Workflow: {cloned_workflow['id']}")
        
        # Klonlanan workflow'un node'larını kontrol et
        cloned_nodes = orchestration.node_get_by_workflow(session, cloned_workflow['id'])
        print(f"Cloned workflow has {len(cloned_nodes)} nodes")
        
        # Klonlanan workflow'un edge'lerini kontrol et
        cloned_edges = orchestration.edge_get_by_workflow(session, cloned_workflow['id'])
        print(f"Cloned workflow has {len(cloned_edges)} edges")
        
        print("\n6. WORKFLOW UPDATE STRUCTURE TEST:")
        print("-" * 30)
        
        # Yeni workflow oluştur
        update_workflow = orchestration.workflow_create(
            session, 
            f'Update Test Workflow {unique_id}',
            'Test workflow for structure update'
        )
        print(f"Update Test Workflow: {update_workflow['id']}")
        
        # İlk node'u ekle
        first_node = orchestration.workflow_add_node(session, update_workflow['id'],
            name='first_node',
            script_id=script1['id'],
            params={'param1': 'first_value'},
            max_retries=3,
            timeout_seconds=300
        )
        
        # Structure'ı güncelle
        new_nodes = [
            {
                'name': 'updated_node1',
                'script_id': script1['id'],
                'params': {'param1': 'updated_value1'},
                'max_retries': 5,
                'timeout_seconds': 600
            },
            {
                'name': 'updated_node2',
                'script_id': script2['id'],
                'params': {'param1': 'updated_value2'},
                'max_retries': 5,
                'timeout_seconds': 600
            }
        ]
        
        new_edges = [
            {
                'from_node_id': 'updated_node1',  # Bu ID mapping yapılacak
                'to_node_id': 'updated_node2',
                'condition_type': 'success'
            }
        ]
        
        # Structure'ı güncelle
        updated_workflow = orchestration.workflow_update_structure(
            session, 
            update_workflow['id'], 
            nodes=new_nodes, 
            edges=None  # Edge'leri şimdilik güncelleme
        )
        print(f"Updated workflow structure")
        
        # Güncellenmiş node'ları kontrol et
        updated_nodes = orchestration.node_get_by_workflow(session, update_workflow['id'])
        print(f"Updated workflow has {len(updated_nodes)} nodes")
        
        print("\n7. FINAL VERIFICATION:")
        print("-" * 30)
        
        # Tüm workflow'ları listele
        all_workflows = orchestration.workflow_list(session)
        print(f"Total workflows: {len(all_workflows)}")
        
        # Node ve edge sayılarını kontrol et
        original_nodes = orchestration.node_get_by_workflow(session, workflow_id)
        original_edges = orchestration.edge_get_by_workflow(session, workflow_id)
        
        cloned_nodes = orchestration.node_get_by_workflow(session, cloned_workflow['id'])
        cloned_edges = orchestration.edge_get_by_workflow(session, cloned_workflow['id'])
        
        print(f"Original workflow: {len(original_nodes)} nodes, {len(original_edges)} edges")
        print(f"Cloned workflow: {len(cloned_nodes)} nodes, {len(cloned_edges)} edges")
        print(f"Updated workflow: {len(updated_nodes)} nodes")

if __name__ == "__main__":
    test_workflow_batch_operations()
