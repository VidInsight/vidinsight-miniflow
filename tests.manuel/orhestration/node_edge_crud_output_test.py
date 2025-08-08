#!/usr/bin/env python3
"""
Node ve Edge CRUD fonksiyonlarının çıktılarını test eder
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

def test_node_edge_crud_outputs():
    """Node ve Edge CRUD fonksiyonlarının çıktılarını test eder"""
    
    print("=" * 80)
    print("NODE AND EDGE CRUD FUNCTIONS OUTPUT TEST")
    print("=" * 80)
    
    # Database setup
    config = get_sqlite_config(db_name='test_node_edge_crud_output.db')
    engine = DatabaseEngine(config)
    engine.create_tables(Base.metadata)
    orchestration = DatabaseOrchestration()
    
    with engine.get_session_context() as session:
        
        unique_id = uuid.uuid4().hex[:8]
        
        print("\n1. WORKFLOW AND SCRIPT CREATE:")
        print("-" * 50)
        
        # Workflow oluştur
        workflow = orchestration.workflow_create(
            session, 
            f'Node Edge Test Workflow {unique_id}',
            'Test workflow for node and edge CRUD operations'
        )
        workflow_id = workflow['id']
        print(f"Workflow Created: {workflow_id}")
        
        # Script oluştur
        script = orchestration.script_create(session,
            name=f'Node Edge Test Script {unique_id}',
            description='Test script for node and edge CRUD operations',
            language=ScriptType.PYTHON,
            type='python',
            script_path='/path/to/node_edge_script.py',
            input_params={'param1': 'string'},
            output_params={'result': 'string'},
            test_status='untested'
        )
        script_id = script['id']
        print(f"Script Created: {script_id}")
        
        print("\n2. NODE CRUD OUTPUTS:")
        print("-" * 50)
        
        # Node'ları ekle
        node1 = orchestration.workflow_add_node(
            session, workflow_id,
            name='test_node1',
            script_id=script_id,
            params={'param1': 'value1'},
            max_retries=3,
            timeout_seconds=300
        )
        node1_id = node1['id']
        
        node2 = orchestration.workflow_add_node(
            session, workflow_id,
            name='test_node2',
            script_id=script_id,
            params={'param1': 'value2'},
            max_retries=5,
            timeout_seconds=600
        )
        node2_id = node2['id']
        
        print("\n2.1. NODE GET OUTPUT:")
        print("-" * 30)
        node_get = orchestration.node_get(session, node1_id)
        print(f"Return Type: {type(node_get)}")
        print(f"Return Keys: {list(node_get.keys())}")
        print(f"Full Output: {json.dumps(node_get, indent=2)}")
        
        print("\n2.2. NODE EXISTS OUTPUT:")
        print("-" * 30)
        node_exists = orchestration.node_exists(session, node1_id)
        print(f"Return Type: {type(node_exists)}")
        print(f"Return Value: {node_exists}")
        
        print("\n2.3. NODE COUNT OUTPUT:")
        print("-" * 30)
        node_count = orchestration.node_count(session)
        print(f"Return Type: {type(node_count)}")
        print(f"Return Value: {node_count}")
        
        print("\n2.4. NODE FILTER OUTPUT:")
        print("-" * 30)
        node_filter = orchestration.node_filter(session, {'workflow_id': workflow_id})
        print(f"Return Type: {type(node_filter)}")
        print(f"List Length: {len(node_filter)}")
        print(f"List Content: {node_filter}")
        
        print("\n2.5. NODE GET BY WORKFLOW OUTPUT:")
        print("-" * 30)
        node_get_by_workflow = orchestration.node_get_by_workflow(session, workflow_id)
        print(f"Return Type: {type(node_get_by_workflow)}")
        print(f"List Length: {len(node_get_by_workflow)}")
        print(f"List Content: {node_get_by_workflow}")
        
        print("\n3. EDGE CRUD OUTPUTS:")
        print("-" * 50)
        
        # Edge ekle
        edge1 = orchestration.workflow_add_edge(
            session, workflow_id,
            from_node_id=node1_id,
            to_node_id=node2_id,
            condition_type='success'
        )
        edge1_id = edge1['id']
        
        edge2 = orchestration.workflow_add_edge(
            session, workflow_id,
            from_node_id=node2_id,
            to_node_id=node1_id,
            condition_type='failure'
        )
        edge2_id = edge2['id']
        
        print("\n3.1. EDGE GET OUTPUT:")
        print("-" * 30)
        edge_get = orchestration.edge_get(session, edge1_id)
        print(f"Return Type: {type(edge_get)}")
        print(f"Return Keys: {list(edge_get.keys())}")
        print(f"Full Output: {json.dumps(edge_get, indent=2)}")
        
        print("\n3.2. EDGE EXISTS OUTPUT:")
        print("-" * 30)
        edge_exists = orchestration.edge_exists(session, edge1_id)
        print(f"Return Type: {type(edge_exists)}")
        print(f"Return Value: {edge_exists}")
        
        print("\n3.3. EDGE COUNT OUTPUT:")
        print("-" * 30)
        edge_count = orchestration.edge_count(session)
        print(f"Return Type: {type(edge_count)}")
        print(f"Return Value: {edge_count}")
        
        print("\n3.4. EDGE FILTER OUTPUT:")
        print("-" * 30)
        edge_filter = orchestration.edge_filter(session, {'workflow_id': workflow_id})
        print(f"Return Type: {type(edge_filter)}")
        print(f"List Length: {len(edge_filter)}")
        print(f"List Content: {edge_filter}")
        
        print("\n3.5. EDGE GET BY WORKFLOW OUTPUT:")
        print("-" * 30)
        edge_get_by_workflow = orchestration.edge_get_by_workflow(session, workflow_id)
        print(f"Return Type: {type(edge_get_by_workflow)}")
        print(f"List Length: {len(edge_get_by_workflow)}")
        print(f"List Content: {edge_get_by_workflow}")
        
        print("\n4. ERROR HANDLING TEST:")
        print("-" * 50)
        
        # Olmayan node'u getirmeye çalış
        try:
            orchestration.node_get(session, 'NONEXISTENT-NODE')
        except Exception as e:
            print(f"Expected Error (node_get): {type(e).__name__}: {str(e)}")
        
        # Olmayan edge'i getirmeye çalış
        try:
            orchestration.edge_get(session, 'NONEXISTENT-EDGE')
        except Exception as e:
            print(f"Expected Error (edge_get): {type(e).__name__}: {str(e)}")
        
        # Olmayan workflow'dan edge'leri getirmeye çalış
        try:
            orchestration.edge_get_by_workflow(session, 'NONEXISTENT-WORKFLOW')
        except Exception as e:
            print(f"Expected Error (edge_get_by_workflow): {type(e).__name__}: {str(e)}")
        
        print("\n5. FILTER TESTING:")
        print("-" * 50)
        
        # Node filtreleme testleri
        print("\n5.1. Node Filter by Script ID:")
        node_filter_by_script = orchestration.node_filter(session, {'script_id': script_id})
        print(f"Nodes with script_id {script_id}: {len(node_filter_by_script)}")
        
        print("\n5.2. Node Filter by Name:")
        node_filter_by_name = orchestration.node_filter(session, {'name': 'test_node1'})
        print(f"Nodes with name 'test_node1': {len(node_filter_by_name)}")
        
        # Edge filtreleme testleri
        print("\n5.3. Edge Filter by Condition Type:")
        edge_filter_by_condition = orchestration.edge_filter(session, {'condition_type': 'success'})
        print(f"Edges with condition_type 'success': {len(edge_filter_by_condition)}")
        
        print("\n5.4. Edge Filter by From Node:")
        edge_filter_by_from = orchestration.edge_filter(session, {'from_node_id': node1_id})
        print(f"Edges from node {node1_id}: {len(edge_filter_by_from)}")
        
        print("\n6. SUMMARY OF NODE AND EDGE CRUD OUTPUT FORMATS:")
        print("-" * 50)
        print("✅ node_get: dict (node bilgileri)")
        print("✅ node_exists: bool (varlık kontrolü)")
        print("✅ node_count: int (toplam node sayısı)")
        print("✅ node_filter: List[str] (filtrelenmiş node ID'leri)")
        print("✅ node_get_by_workflow: List[str] (workflow'daki node ID'leri)")
        print("✅ edge_get: dict (edge bilgileri)")
        print("✅ edge_exists: bool (varlık kontrolü)")
        print("✅ edge_count: int (toplam edge sayısı)")
        print("✅ edge_filter: List[str] (filtrelenmiş edge ID'leri)")
        print("✅ edge_get_by_workflow: List[str] (workflow'daki edge ID'leri)")

if __name__ == "__main__":
    test_node_edge_crud_outputs()
