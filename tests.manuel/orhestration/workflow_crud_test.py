#!/usr/bin/env python3
"""
Workflow, Node ve Edge CRUD fonksiyonlarını test eder
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from miniflow.database_manager.config import get_sqlite_config
from miniflow.database_manager.engine import DatabaseEngine
from miniflow.database_manager.orchestration import DatabaseOrchestration
from miniflow.database_manager.models import Base, ScriptType
import uuid

def test_workflow_crud():
    """Workflow, Node ve Edge CRUD fonksiyonlarını test eder"""
    
    print("=" * 60)
    print("WORKFLOW, NODE VE EDGE CRUD TEST")
    print("=" * 60)
    
    # Database setup
    config = get_sqlite_config(db_name='test_workflow_crud.db')
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
            'Test workflow for CRUD operations'
        )
        print(f"Workflow Created: {workflow['id']}")
        workflow_id = workflow['id']
        
        print("\n2. SCRIPT CREATE TEST:")
        print("-" * 30)
        
        # Script oluştur
        script = orchestration.script_create(session,
            name=f'Test Script {unique_id}',
            description='Test script for node operations',
            language=ScriptType.PYTHON,
            type='python',
            script_path='/path/to/test_script.py',
            input_params={'param1': 'string'},
            output_params={'result': 'string'},
            test_status='untested'
        )
        print(f"Script Created: {script['id']}")
        script_id = script['id']
        
        print("\n3. WORKFLOW ADD NODE TEST:")
        print("-" * 30)
        
        # Node ekle
        node_data = {
            'name': 'test_node',
            'script_id': script_id,
            'params': {'param1': 'value1'},
            'max_retries': 3,
            'timeout_seconds': 300
        }
        
        node = orchestration.workflow_add_node(session, workflow_id, **node_data)
        print(f"Node Added: {node['id']}")
        node_id = node['id']
        
        print("\n4. NODE GET TEST:")
        print("-" * 30)
        
        # Node get
        retrieved_node = orchestration.node_get(session, node_id)
        print(f"Node Retrieved: {retrieved_node['name']}")
        
        print("\n5. NODE EXISTS TEST:")
        print("-" * 30)
        
        # Node exists
        node_exists = orchestration.node_exists(session, node_id)
        print(f"Node Exists: {node_exists}")
        
        print("\n6. NODE COUNT TEST:")
        print("-" * 30)
        
        # Node count
        node_count = orchestration.node_count(session)
        print(f"Total Nodes: {node_count}")
        
        print("\n7. NODE FILTER TEST:")
        print("-" * 30)
        
        # Node filter
        filtered_nodes = orchestration.node_filter(session, {'workflow_id': workflow_id})
        print(f"Filtered Nodes: {len(filtered_nodes)}")
        
        print("\n8. NODE GET BY WORKFLOW TEST:")
        print("-" * 30)
        
        # Node get by workflow
        workflow_nodes = orchestration.node_get_by_workflow(session, workflow_id)
        print(f"Workflow Nodes: {len(workflow_nodes)}")
        
        print("\n9. WORKFLOW ADD EDGE TEST:")
        print("-" * 30)
        
        # İkinci node oluştur
        node_data2 = {
            'name': 'test_node_2',
            'script_id': script_id,
            'params': {'param1': 'value2'},
            'max_retries': 3,
            'timeout_seconds': 300
        }
        
        node2 = orchestration.workflow_add_node(session, workflow_id, **node_data2)
        print(f"Second Node Added: {node2['id']}")
        node2_id = node2['id']
        
        # Edge ekle
        edge = orchestration.workflow_add_edge(
            session, 
            workflow_id, 
            node_id, 
            node2_id, 
            'success'
        )
        print(f"Edge Added: {edge['id']}")
        edge_id = edge['id']
        
        print("\n10. EDGE GET TEST:")
        print("-" * 30)
        
        # Edge get
        retrieved_edge = orchestration.edge_get(session, edge_id)
        print(f"Edge Retrieved: {retrieved_edge['id']}")
        
        print("\n11. EDGE EXISTS TEST:")
        print("-" * 30)
        
        # Edge exists
        edge_exists = orchestration.edge_exists(session, edge_id)
        print(f"Edge Exists: {edge_exists}")
        
        print("\n12. EDGE COUNT TEST:")
        print("-" * 30)
        
        # Edge count
        edge_count = orchestration.edge_count(session)
        print(f"Total Edges: {edge_count}")
        
        print("\n13. EDGE FILTER TEST:")
        print("-" * 30)
        
        # Edge filter
        filtered_edges = orchestration.edge_filter(session, {'workflow_id': workflow_id})
        print(f"Filtered Edges: {len(filtered_edges)}")
        
        print("\n14. EDGE GET BY WORKFLOW TEST:")
        print("-" * 30)
        
        # Edge get by workflow
        workflow_edges = orchestration.edge_get_by_workflow(session, workflow_id)
        print(f"Workflow Edges: {len(workflow_edges)}")
        
        print("\n15. WORKFLOW REMOVE EDGE TEST:")
        print("-" * 30)
        
        # Edge sil
        deleted_edge = orchestration.workflow_remove_edge(session, workflow_id, edge_id)
        print(f"Edge Removed: {deleted_edge['id']}")
        
        print("\n16. WORKFLOW REMOVE NODE TEST:")
        print("-" * 30)
        
        # Node sil
        deleted_node = orchestration.workflow_remove_node(session, workflow_id, node2_id)
        print(f"Node Removed: {deleted_node['id']}")
        
        print("\n17. FINAL COUNTS TEST:")
        print("-" * 30)
        
        # Final counts
        final_node_count = orchestration.node_count(session)
        final_edge_count = orchestration.edge_count(session)
        print(f"Final Node Count: {final_node_count}")
        print(f"Final Edge Count: {final_edge_count}")

if __name__ == "__main__":
    test_workflow_crud()
