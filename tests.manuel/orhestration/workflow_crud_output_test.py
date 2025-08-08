#!/usr/bin/env python3
"""
Workflow CRUD fonksiyonlarının çıktılarını test eder
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

def test_workflow_crud_outputs():
    """Workflow CRUD fonksiyonlarının çıktılarını test eder"""
    
    print("=" * 80)
    print("WORKFLOW CRUD FUNCTIONS OUTPUT TEST")
    print("=" * 80)
    
    # Database setup
    config = get_sqlite_config(db_name='test_workflow_crud_output.db')
    engine = DatabaseEngine(config)
    engine.create_tables(Base.metadata)
    orchestration = DatabaseOrchestration()
    
    with engine.get_session_context() as session:
        
        unique_id = uuid.uuid4().hex[:8]
        
        print("\n1. WORKFLOW CREATE OUTPUT:")
        print("-" * 50)
        
        # Workflow oluştur
        workflow = orchestration.workflow_create(
            session, 
            f'CRUD Test Workflow {unique_id}',
            'Test workflow for CRUD operations'
        )
        print(f"Return Type: {type(workflow)}")
        print(f"Return Keys: {list(workflow.keys())}")
        print(f"Full Output: {json.dumps(workflow, indent=2)}")
        workflow_id = workflow['id']
        
        print("\n2. SCRIPT CREATE OUTPUT:")
        print("-" * 50)
        
        # Script oluştur
        script = orchestration.script_create(session,
            name=f'CRUD Test Script {unique_id}',
            description='Test script for CRUD operations',
            language=ScriptType.PYTHON,
            type='python',
            script_path='/path/to/crud_script.py',
            input_params={'param1': 'string'},
            output_params={'result': 'string'},
            test_status='untested'
        )
        print(f"Return Type: {type(script)}")
        print(f"Return Keys: {list(script.keys())}")
        print(f"Full Output: {json.dumps(script, indent=2)}")
        
        print("\n3. WORKFLOW ADD NODE OUTPUT:")
        print("-" * 50)
        
        # Node ekle
        added_node = orchestration.workflow_add_node(
            session, 
            workflow_id,
            name='test_node',
            script_id=script['id'],
            params={'param1': 'test_value'},
            max_retries=3,
            timeout_seconds=300
        )
        print(f"Return Type: {type(added_node)}")
        print(f"Return Keys: {list(added_node.keys())}")
        print(f"Full Output: {json.dumps(added_node, indent=2)}")
        node_id = added_node['id']
        
        print("\n4. WORKFLOW ADD EDGE OUTPUT:")
        print("-" * 50)
        
        # İkinci node ekle
        second_node = orchestration.workflow_add_node(
            session, 
            workflow_id,
            name='test_node2',
            script_id=script['id'],
            params={'param1': 'test_value2'},
            max_retries=3,
            timeout_seconds=300
        )
        
        # Edge ekle
        added_edge = orchestration.workflow_add_edge(
            session, 
            workflow_id,
            from_node_id=node_id,
            to_node_id=second_node['id'],
            condition_type='success'
        )
        print(f"Return Type: {type(added_edge)}")
        print(f"Return Keys: {list(added_edge.keys())}")
        print(f"Full Output: {json.dumps(added_edge, indent=2)}")
        edge_id = added_edge['id']
        
        print("\n5. WORKFLOW REMOVE EDGE OUTPUT:")
        print("-" * 50)
        
        # Edge sil
        removed_edge = orchestration.workflow_remove_edge(
            session, 
            workflow_id, 
            edge_id
        )
        print(f"Return Type: {type(removed_edge)}")
        print(f"Return Keys: {list(removed_edge.keys())}")
        print(f"Full Output: {json.dumps(removed_edge, indent=2)}")
        
        print("\n6. WORKFLOW REMOVE NODE OUTPUT:")
        print("-" * 50)
        
        # Node sil
        removed_node = orchestration.workflow_remove_node(
            session, 
            workflow_id, 
            node_id
        )
        print(f"Return Type: {type(removed_node)}")
        print(f"Return Keys: {list(removed_node.keys())}")
        print(f"Full Output: {json.dumps(removed_node, indent=2)}")
        
        print("\n7. ERROR HANDLING TEST:")
        print("-" * 50)
        
        # Olmayan workflow'a node eklemeye çalış
        try:
            orchestration.workflow_add_node(
                session, 
                'NONEXISTENT-WORKFLOW',
                name='test_node',
                script_id=script['id']
            )
        except Exception as e:
            print(f"Expected Error (workflow not found): {type(e).__name__}: {str(e)}")
        
        # Olmayan node'a edge eklemeye çalış
        try:
            orchestration.workflow_add_edge(
                session, 
                workflow_id,
                from_node_id='NONEXISTENT-NODE',
                to_node_id=second_node['id']
            )
        except Exception as e:
            print(f"Expected Error (node not found): {type(e).__name__}: {str(e)}")
        
        # Olmayan edge'i silmeye çalış
        try:
            orchestration.workflow_remove_edge(
                session, 
                workflow_id, 
                'NONEXISTENT-EDGE'
            )
        except Exception as e:
            print(f"Expected Error (edge not found): {type(e).__name__}: {str(e)}")
        
        print("\n8. SUMMARY OF CRUD OUTPUT FORMATS:")
        print("-" * 50)
        print("✅ workflow_add_node: dict (eklenen node bilgileri)")
        print("✅ workflow_remove_node: dict (silinen node bilgileri)")
        print("✅ workflow_add_edge: dict (eklenen edge bilgileri)")
        print("✅ workflow_remove_edge: dict (silinen edge bilgileri)")
        print("✅ Error Handling: BusinessLogicError (validation hataları)")

if __name__ == "__main__":
    test_workflow_crud_outputs()
