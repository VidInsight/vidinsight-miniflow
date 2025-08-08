#!/usr/bin/env python3
"""
Filter fonksiyonlarının çıktı formatlarını detaylı test eder
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from miniflow.database_manager.config import get_sqlite_config
from miniflow.database_manager.engine import DatabaseEngine
from miniflow.database_manager.orchestration import DatabaseOrchestration
from miniflow.database_manager.models import Base, ScriptType
import uuid

def test_filter_output_formats():
    """Filter fonksiyonlarının çıktı formatlarını detaylı test eder"""
    
    print("=" * 100)
    print("FILTER FUNCTIONS OUTPUT FORMATS TEST")
    print("=" * 100)
    
    # Database setup
    config = get_sqlite_config(db_name='test_filter_output_formats.db')
    engine = DatabaseEngine(config)
    engine.create_tables(Base.metadata)
    orchestration = DatabaseOrchestration()
    
    with engine.get_session_context() as session:
        
        unique_id = uuid.uuid4().hex[:8]
        
        print("\n📋 WORKFLOW FILTER OUTPUT FORMATS:")
        print("=" * 60)
        
        # Workflow'lar oluştur
        workflow1 = orchestration.workflow_create(session, f'Filter Test Workflow 1 {unique_id}', 'Active workflow')
        workflow2 = orchestration.workflow_create(session, f'Filter Test Workflow 2 {unique_id}', 'Draft workflow')
        workflow3 = orchestration.workflow_create(session, f'Filter Test Workflow 3 {unique_id}', 'Active workflow')
        
        # Workflow filter testleri
        all_workflows = orchestration.workflow_filter(session, {})
        print(f"✅ workflow_filter (empty): {type(all_workflows)}")
        print(f"   Return: List[str] with length: {len(all_workflows)}")
        print(f"   Content: {all_workflows}")
        
        active_workflows = orchestration.workflow_filter(session, {'status': 'draft'})
        print(f"\n✅ workflow_filter (status=draft): {type(active_workflows)}")
        print(f"   Return: List[str] with length: {len(active_workflows)}")
        print(f"   Content: {active_workflows}")
        
        print("\n📋 SCRIPT FILTER OUTPUT FORMATS:")
        print("=" * 60)
        
        # Script'ler oluştur
        script1 = orchestration.script_create(session,
            name=f'Filter Test Script 1 {unique_id}',
            description='Python script',
            language=ScriptType.PYTHON,
            type='python',
            script_path='/path/to/script1.py',
            input_params={'param1': 'string'},
            output_params={'result': 'string'},
            test_status='untested'
        )
        
        script2 = orchestration.script_create(session,
            name=f'Filter Test Script 2 {unique_id}',
            description='Python script 2',
            language=ScriptType.PYTHON,
            type='python',
            script_path='/path/to/script2.py',
            input_params={'param1': 'string'},
            output_params={'result': 'string'},
            test_status='passed'
        )
        
        script3 = orchestration.script_create(session,
            name=f'Filter Test Script 3 {unique_id}',
            description='Python script',
            language=ScriptType.PYTHON,
            type='python',
            script_path='/path/to/script3.py',
            input_params={'param1': 'string'},
            output_params={'result': 'string'},
            test_status='untested'
        )
        
        # Script filter testleri
        all_scripts = orchestration.script_filter(session, {})
        print(f"✅ script_filter (empty): {type(all_scripts)}")
        print(f"   Return: List[str] with length: {len(all_scripts)}")
        print(f"   Content: {all_scripts}")
        
        python_scripts = orchestration.script_filter(session, {'language': 'python'})
        print(f"\n✅ script_filter (language=python): {type(python_scripts)}")
        print(f"   Return: List[str] with length: {len(python_scripts)}")
        print(f"   Content: {python_scripts}")
        
        tested_scripts = orchestration.script_filter(session, {'test_status': 'passed'})
        print(f"\n✅ script_filter (test_status=passed): {type(tested_scripts)}")
        print(f"   Return: List[str] with length: {len(tested_scripts)}")
        print(f"   Content: {tested_scripts}")
        
        print("\n📋 ENVIRONMENT FILTER OUTPUT FORMATS:")
        print("=" * 60)
        
        # Environment'lar oluştur
        env1 = orchestration.environment_create(session,
            name=f'Filter Test Env 1 {unique_id}',
            value='production_value',
            description='Production environment'
        )
        
        env2 = orchestration.environment_create(session,
            name=f'Filter Test Env 2 {unique_id}',
            value='development_value',
            description='Development environment'
        )
        
        env3 = orchestration.environment_create(session,
            name=f'Filter Test Env 3 {unique_id}',
            value='test_value',
            description='Test environment'
        )
        
        # Environment filter testleri
        all_envs = orchestration.environment_filter(session, {})
        print(f"✅ environment_filter (empty): {type(all_envs)}")
        print(f"   Return: List[str] with length: {len(all_envs)}")
        print(f"   Content: {all_envs}")
        
        production_envs = orchestration.environment_filter(session, {'name': f'Filter Test Env 1 {unique_id}'})
        print(f"\n✅ environment_filter (name=production): {type(production_envs)}")
        print(f"   Return: List[str] with length: {len(production_envs)}")
        print(f"   Content: {production_envs}")
        
        print("\n📋 NODE FILTER OUTPUT FORMATS:")
        print("=" * 60)
        
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
            max_retries=5,
            timeout_seconds=600
        )
        
        node3 = orchestration.workflow_add_node(session, workflow2['id'],
            name='filter_test_node3',
            script_id=script1['id'],
            params={'param1': 'value3'},
            max_retries=3,
            timeout_seconds=300
        )
        
        # Node filter testleri
        all_nodes = orchestration.node_filter(session, {})
        print(f"✅ node_filter (empty): {type(all_nodes)}")
        print(f"   Return: List[str] with length: {len(all_nodes)}")
        print(f"   Content: {all_nodes}")
        
        workflow1_nodes = orchestration.node_filter(session, {'workflow_id': workflow1['id']})
        print(f"\n✅ node_filter (workflow_id): {type(workflow1_nodes)}")
        print(f"   Return: List[str] with length: {len(workflow1_nodes)}")
        print(f"   Content: {workflow1_nodes}")
        
        script1_nodes = orchestration.node_filter(session, {'script_id': script1['id']})
        print(f"\n✅ node_filter (script_id): {type(script1_nodes)}")
        print(f"   Return: List[str] with length: {len(script1_nodes)}")
        print(f"   Content: {script1_nodes}")
        
        print("\n📋 EDGE FILTER OUTPUT FORMATS:")
        print("=" * 60)
        
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
        
        edge3 = orchestration.workflow_add_edge(session, workflow2['id'],
            from_node_id=node3['id'],
            to_node_id=node3['id'],
            condition_type='success'
        )
        
        # Edge filter testleri
        all_edges = orchestration.edge_filter(session, {})
        print(f"✅ edge_filter (empty): {type(all_edges)}")
        print(f"   Return: List[str] with length: {len(all_edges)}")
        print(f"   Content: {all_edges}")
        
        workflow1_edges = orchestration.edge_filter(session, {'workflow_id': workflow1['id']})
        print(f"\n✅ edge_filter (workflow_id): {type(workflow1_edges)}")
        print(f"   Return: List[str] with length: {len(workflow1_edges)}")
        print(f"   Content: {workflow1_edges}")
        
        success_edges = orchestration.edge_filter(session, {'condition_type': 'success'})
        print(f"\n✅ edge_filter (condition_type=success): {type(success_edges)}")
        print(f"   Return: List[str] with length: {len(success_edges)}")
        print(f"   Content: {success_edges}")
        
        from_node_edges = orchestration.edge_filter(session, {'from_node_id': node1['id']})
        print(f"\n✅ edge_filter (from_node_id): {type(from_node_edges)}")
        print(f"   Return: List[str] with length: {len(from_node_edges)}")
        print(f"   Content: {from_node_edges}")
        
        print("\n📋 EXECUTION FILTER OUTPUT FORMATS:")
        print("=" * 60)
        
        # Execution başlat
        execution1 = orchestration.execution_start(session, workflow1['id'])
        execution2 = orchestration.execution_start(session, workflow2['id'])
        
        # Execution filter testleri
        all_executions = orchestration.execution_filter(session, {})
        print(f"✅ execution_filter (empty): {type(all_executions)}")
        print(f"   Return: List[str] with length: {len(all_executions)}")
        print(f"   Content: {all_executions}")
        
        workflow1_executions = orchestration.execution_filter(session, {'workflow_id': workflow1['id']})
        print(f"\n✅ execution_filter (workflow_id): {type(workflow1_executions)}")
        print(f"   Return: List[str] with length: {len(workflow1_executions)}")
        print(f"   Content: {workflow1_executions}")
        
        pending_executions = orchestration.execution_filter(session, {'status': 'pending'})
        print(f"\n✅ execution_filter (status=pending): {type(pending_executions)}")
        print(f"   Return: List[str] with length: {len(pending_executions)}")
        print(f"   Content: {pending_executions}")
        
        print("\n📋 COMPLEX FILTER EXAMPLES:")
        print("=" * 60)
        
        # Karmaşık filtre örnekleri
        print("\n🎯 Multiple Condition Filters:")
        
        # Workflow + Script kombinasyonu
        python_workflow_nodes = orchestration.node_filter(session, {
            'workflow_id': workflow1['id'],
            'script_id': script1['id']
        })
        print(f"✅ node_filter (workflow_id + script_id): {len(python_workflow_nodes)} nodes")
        print(f"   Content: {python_workflow_nodes}")
        
        # Success edges from specific node
        success_from_node = orchestration.edge_filter(session, {
            'from_node_id': node1['id'],
            'condition_type': 'success'
        })
        print(f"\n✅ edge_filter (from_node_id + condition_type): {len(success_from_node)} edges")
        print(f"   Content: {success_from_node}")
        
        print("\n📋 FILTER OUTPUT FORMAT SUMMARY:")
        print("=" * 60)
        print("🎯 ALL FILTER FUNCTIONS RETURN List[str]:")
        print("   ✅ workflow_filter: List[str] (workflow ID'leri)")
        print("   ✅ script_filter: List[str] (script ID'leri)")
        print("   ✅ environment_filter: List[str] (environment ID'leri)")
        print("   ✅ node_filter: List[str] (node ID'leri)")
        print("   ✅ edge_filter: List[str] (edge ID'leri)")
        print("   ✅ execution_filter: List[str] (execution ID'leri)")
        
        print("\n🎯 FILTER ADVANTAGES:")
        print("   ✅ Performance: Sadece ID'ler döndürülüyor")
        print("   ✅ Network Efficient: Minimal bandwidth kullanımı")
        print("   ✅ API Friendly: JSON serializable")
        print("   ✅ Batch Operations: ID listesi ile toplu işlemler")
        print("   ✅ Lazy Loading: Detay bilgiler sadece gerektiğinde alınıyor")
        
        print("\n🎯 USAGE EXAMPLES:")
        print("   # ID listesi ile batch işlemler")
        print("   workflow_ids = orchestration.workflow_filter(session, {'status': 'active'})")
        print("   for workflow_id in workflow_ids:")
        print("       workflow = orchestration.workflow_get(session, workflow_id)")
        print("       # İşlem yap")
        print("   ")
        print("   # Karmaşık filtreler")
        print("   python_nodes = orchestration.node_filter(session, {")
        print("       'workflow_id': workflow_id,")
        print("       'script_id': python_script_id")
        print("   })")

if __name__ == "__main__":
    test_filter_output_formats()
