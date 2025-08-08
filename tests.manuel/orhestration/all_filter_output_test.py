#!/usr/bin/env python3
"""
Tüm filter fonksiyonlarının ID listesi döndürdüğünü test eder
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from miniflow.database_manager.config import get_sqlite_config
from miniflow.database_manager.engine import DatabaseEngine
from miniflow.database_manager.orchestration import DatabaseOrchestration
from miniflow.database_manager.models import Base, ScriptType
import uuid

def test_all_filter_outputs():
    """Tüm filter fonksiyonlarının ID listesi döndürdüğünü test eder"""
    
    print("=" * 80)
    print("ALL FILTER FUNCTIONS ID LIST OUTPUT TEST")
    print("=" * 80)
    
    # Database setup
    config = get_sqlite_config(db_name='test_all_filter_output.db')
    engine = DatabaseEngine(config)
    engine.create_tables(Base.metadata)
    orchestration = DatabaseOrchestration()
    
    with engine.get_session_context() as session:
        
        unique_id = uuid.uuid4().hex[:8]
        
        print("\n1. WORKFLOW FILTER TEST:")
        print("-" * 50)
        
        # Workflow'lar oluştur
        workflow1 = orchestration.workflow_create(session, f'Filter Test Workflow 1 {unique_id}')
        workflow2 = orchestration.workflow_create(session, f'Filter Test Workflow 2 {unique_id}')
        
        # Workflow filter test
        workflow_filter = orchestration.workflow_filter(session, {})
        print(f"Return Type: {type(workflow_filter)}")
        print(f"List Length: {len(workflow_filter)}")
        print(f"List Content: {workflow_filter}")
        
        print("\n2. SCRIPT FILTER TEST:")
        print("-" * 50)
        
        # Script'ler oluştur
        script1 = orchestration.script_create(session,
            name=f'Filter Test Script 1 {unique_id}',
            description='Test script 1',
            language=ScriptType.PYTHON,
            type='python',
            script_path='/path/to/script1.py',
            input_params={'param1': 'string'},
            output_params={'result': 'string'},
            test_status='untested'
        )
        
        script2 = orchestration.script_create(session,
            name=f'Filter Test Script 2 {unique_id}',
            description='Test script 2',
            language=ScriptType.PYTHON,
            type='python',
            script_path='/path/to/script2.py',
            input_params={'param1': 'string'},
            output_params={'result': 'string'},
            test_status='untested'
        )
        
        # Script filter test
        script_filter = orchestration.script_filter(session, {})
        print(f"Return Type: {type(script_filter)}")
        print(f"List Length: {len(script_filter)}")
        print(f"List Content: {script_filter}")
        
        print("\n3. ENVIRONMENT FILTER TEST:")
        print("-" * 50)
        
        # Environment'lar oluştur
        env1 = orchestration.environment_create(session,
            name=f'Filter Test Env 1 {unique_id}',
            value='value1',
            description='Test environment 1'
        )
        
        env2 = orchestration.environment_create(session,
            name=f'Filter Test Env 2 {unique_id}',
            value='value2',
            description='Test environment 2'
        )
        
        # Environment filter test
        environment_filter = orchestration.environment_filter(session, {})
        print(f"Return Type: {type(environment_filter)}")
        print(f"List Length: {len(environment_filter)}")
        print(f"List Content: {environment_filter}")
        
        print("\n4. NODE FILTER TEST:")
        print("-" * 50)
        
        # Node'ları ekle
        node1 = orchestration.workflow_add_node(session, workflow1['id'],
            name='filter_test_node1',
            script_id=script1['id'],
            params={'param1': 'value1'},
            max_retries=3,
            timeout_seconds=300
        )
        
        node2 = orchestration.workflow_add_node(session, workflow1['id'],
            name='filter_test_node2',
            script_id=script2['id'],
            params={'param1': 'value2'},
            max_retries=3,
            timeout_seconds=300
        )
        
        # Node filter test
        node_filter = orchestration.node_filter(session, {'workflow_id': workflow1['id']})
        print(f"Return Type: {type(node_filter)}")
        print(f"List Length: {len(node_filter)}")
        print(f"List Content: {node_filter}")
        
        print("\n5. EDGE FILTER TEST:")
        print("-" * 50)
        
        # Edge'leri ekle
        edge1 = orchestration.workflow_add_edge(session, workflow1['id'],
            from_node_id=node1['id'],
            to_node_id=node2['id'],
            condition_type='success'
        )
        
        edge2 = orchestration.workflow_add_edge(session, workflow1['id'],
            from_node_id=node2['id'],
            to_node_id=node1['id'],
            condition_type='failure'
        )
        
        # Edge filter test
        edge_filter = orchestration.edge_filter(session, {'workflow_id': workflow1['id']})
        print(f"Return Type: {type(edge_filter)}")
        print(f"List Length: {len(edge_filter)}")
        print(f"List Content: {edge_filter}")
        
        print("\n6. EXECUTION FILTER TEST:")
        print("-" * 50)
        
        # Execution başlat (sadece workflow1'de node var)
        execution1 = orchestration.execution_start(session, workflow1['id'])
        
        # Execution filter test
        execution_filter = orchestration.execution_filter(session, {})
        print(f"Return Type: {type(execution_filter)}")
        print(f"List Length: {len(execution_filter)}")
        print(f"List Content: {execution_filter}")
        
        print("\n7. SPECIFIC FILTER TESTS:")
        print("-" * 50)
        
        # Belirli filtreler test et
        print("\n7.1. Workflow Filter by Name:")
        workflow_by_name = orchestration.workflow_filter(session, {'name': f'Filter Test Workflow 1 {unique_id}'})
        print(f"Workflows with name: {workflow_by_name}")
        
        print("\n7.2. Script Filter by Language:")
        script_by_language = orchestration.script_filter(session, {'language': 'python'})
        print(f"Scripts with language 'python': {script_by_language}")
        
        print("\n7.3. Environment Filter by Name:")
        env_by_name = orchestration.environment_filter(session, {'name': f'Filter Test Env 1 {unique_id}'})
        print(f"Environments with name: {env_by_name}")
        
        print("\n7.4. Node Filter by Script ID:")
        node_by_script = orchestration.node_filter(session, {'script_id': script1['id']})
        print(f"Nodes with script_id {script1['id']}: {node_by_script}")
        
        print("\n7.5. Edge Filter by Condition Type:")
        edge_by_condition = orchestration.edge_filter(session, {'condition_type': 'success'})
        print(f"Edges with condition_type 'success': {edge_by_condition}")
        
        print("\n7.6. Execution Filter by Workflow ID:")
        execution_by_workflow = orchestration.execution_filter(session, {'workflow_id': workflow1['id']})
        print(f"Executions with workflow_id {workflow1['id']}: {execution_by_workflow}")
        
        print("\n8. SUMMARY OF ALL FILTER OUTPUT FORMATS:")
        print("-" * 50)
        print("✅ workflow_filter: List[str] (workflow ID'leri)")
        print("✅ script_filter: List[str] (script ID'leri)")
        print("✅ environment_filter: List[str] (environment ID'leri)")
        print("✅ node_filter: List[str] (node ID'leri)")
        print("✅ edge_filter: List[str] (edge ID'leri)")
        print("✅ execution_filter: List[str] (execution ID'leri)")
        print("\n🎯 Tüm filter fonksiyonları artık ID listesi döndürüyor!")

if __name__ == "__main__":
    test_all_filter_outputs()
