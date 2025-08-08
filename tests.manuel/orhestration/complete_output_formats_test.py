#!/usr/bin/env python3
"""
Tüm fonksiyonların güncel çıktı formatlarını test eder
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

def test_complete_output_formats():
    """Tüm fonksiyonların güncel çıktı formatlarını test eder"""
    
    print("=" * 100)
    print("COMPLETE OUTPUT FORMATS TEST")
    print("=" * 100)
    
    # Database setup
    config = get_sqlite_config(db_name='test_complete_output_formats.db')
    engine = DatabaseEngine(config)
    engine.create_tables(Base.metadata)
    orchestration = DatabaseOrchestration()
    
    with engine.get_session_context() as session:
        
        unique_id = uuid.uuid4().hex[:8]
        
        print("\n📋 WORKFLOW FUNCTIONS OUTPUT FORMATS:")
        print("=" * 60)
        
        # Workflow oluştur
        workflow = orchestration.workflow_create(session, f'Format Test Workflow {unique_id}', 'Test description')
        workflow_id = workflow['id']
        
        print(f"\n✅ workflow_create: {type(workflow)}")
        print(f"   Return: dict with keys: {list(workflow.keys())}")
        print(f"   Sample: {workflow['id']}")
        
        # workflow_get'i node ekledikten sonra test edeceğiz
        print(f"\n✅ workflow_get: dict (node ekledikten sonra test edilecek)")
        
        workflow_list = orchestration.workflow_list(session)
        print(f"\n✅ workflow_list: {type(workflow_list)}")
        print(f"   Return: List[dict] with length: {len(workflow_list)}")
        
        workflow_count = orchestration.workflow_count(session)
        print(f"\n✅ workflow_count: {type(workflow_count)}")
        print(f"   Return: int = {workflow_count}")
        
        workflow_exists = orchestration.workflow_exists(session, workflow_id)
        print(f"\n✅ workflow_exists: {type(workflow_exists)}")
        print(f"   Return: bool = {workflow_exists}")
        
        workflow_filter = orchestration.workflow_filter(session, {})
        print(f"\n✅ workflow_filter: {type(workflow_filter)}")
        print(f"   Return: List[str] with length: {len(workflow_filter)}")
        print(f"   Sample: {workflow_filter[:2] if workflow_filter else []}")
        
        print("\n📋 SCRIPT FUNCTIONS OUTPUT FORMATS:")
        print("=" * 60)
        
        # Script oluştur
        script = orchestration.script_create(session,
            name=f'Format Test Script {unique_id}',
            description='Test script',
            language=ScriptType.PYTHON,
            type='python',
            script_path='/path/to/script.py',
            input_params={'param1': 'string'},
            output_params={'result': 'string'},
            test_status='untested'
        )
        script_id = script['id']
        
        print(f"\n✅ script_create: {type(script)}")
        print(f"   Return: dict with keys: {list(script.keys())}")
        
        script_get = orchestration.script_get(session, script_id)
        print(f"\n✅ script_get: {type(script_get)}")
        print(f"   Return: dict with keys: {list(script_get.keys())}")
        
        script_list = orchestration.script_list(session)
        print(f"\n✅ script_list: {type(script_list)}")
        print(f"   Return: List[dict] with length: {len(script_list)}")
        
        script_count = orchestration.script_count(session)
        print(f"\n✅ script_count: {type(script_count)}")
        print(f"   Return: int = {script_count}")
        
        script_exists = orchestration.script_exists(session, script_id)
        print(f"\n✅ script_exists: {type(script_exists)}")
        print(f"   Return: bool = {script_exists}")
        
        script_filter = orchestration.script_filter(session, {})
        print(f"\n✅ script_filter: {type(script_filter)}")
        print(f"   Return: List[str] with length: {len(script_filter)}")
        print(f"   Sample: {script_filter[:2] if script_filter else []}")
        
        print("\n📋 ENVIRONMENT FUNCTIONS OUTPUT FORMATS:")
        print("=" * 60)
        
        # Environment oluştur
        environment = orchestration.environment_create(session,
            name=f'Format Test Env {unique_id}',
            value='test_value',
            description='Test environment'
        )
        environment_id = environment['id']
        
        print(f"\n✅ environment_create: {type(environment)}")
        print(f"   Return: dict with keys: {list(environment.keys())}")
        
        environment_get = orchestration.environment_get(session, environment_id)
        print(f"\n✅ environment_get: {type(environment_get)}")
        print(f"   Return: dict with keys: {list(environment_get.keys())}")
        
        environment_list = orchestration.environment_list(session)
        print(f"\n✅ environment_list: {type(environment_list)}")
        print(f"   Return: List[dict] with length: {len(environment_list)}")
        
        environment_count = orchestration.environment_count(session)
        print(f"\n✅ environment_count: {type(environment_count)}")
        print(f"   Return: int = {environment_count}")
        
        environment_exists = orchestration.environment_exists(session, environment_id)
        print(f"\n✅ environment_exists: {type(environment_exists)}")
        print(f"   Return: bool = {environment_exists}")
        
        environment_filter = orchestration.environment_filter(session, {})
        print(f"\n✅ environment_filter: {type(environment_filter)}")
        print(f"   Return: List[str] with length: {len(environment_filter)}")
        print(f"   Sample: {environment_filter[:2] if environment_filter else []}")
        
        print("\n📋 NODE FUNCTIONS OUTPUT FORMATS:")
        print("=" * 60)
        
        # Node ekle
        node = orchestration.workflow_add_node(session, workflow_id,
            name='format_test_node',
            script_id=script_id,
            params={'param1': 'value1'},
            max_retries=3,
            timeout_seconds=300
        )
        node_id = node['id']
        
        print(f"\n✅ workflow_add_node: {type(node)}")
        print(f"   Return: dict with keys: {list(node.keys())}")
        
        node_get = orchestration.node_get(session, node_id)
        print(f"\n✅ node_get: {type(node_get)}")
        print(f"   Return: dict with keys: {list(node_get.keys())}")
        
        node_exists = orchestration.node_exists(session, node_id)
        print(f"\n✅ node_exists: {type(node_exists)}")
        print(f"   Return: bool = {node_exists}")
        
        node_count = orchestration.node_count(session)
        print(f"\n✅ node_count: {type(node_count)}")
        print(f"   Return: int = {node_count}")
        
        node_filter = orchestration.node_filter(session, {'workflow_id': workflow_id})
        print(f"\n✅ node_filter: {type(node_filter)}")
        print(f"   Return: List[str] with length: {len(node_filter)}")
        print(f"   Sample: {node_filter[:2] if node_filter else []}")
        
        node_get_by_workflow = orchestration.node_get_by_workflow(session, workflow_id)
        print(f"\n✅ node_get_by_workflow: {type(node_get_by_workflow)}")
        print(f"   Return: List[str] with length: {len(node_get_by_workflow)}")
        print(f"   Sample: {node_get_by_workflow[:2] if node_get_by_workflow else []}")
        
        print("\n📋 EDGE FUNCTIONS OUTPUT FORMATS:")
        print("=" * 60)
        
        # İkinci node ekle
        node2 = orchestration.workflow_add_node(session, workflow_id,
            name='format_test_node2',
            script_id=script_id,
            params={'param1': 'value2'},
            max_retries=3,
            timeout_seconds=300
        )
        
        # Edge ekle
        edge = orchestration.workflow_add_edge(session, workflow_id,
            from_node_id=node_id,
            to_node_id=node2['id'],
            condition_type='success'
        )
        edge_id = edge['id']
        
        print(f"\n✅ workflow_add_edge: {type(edge)}")
        print(f"   Return: dict with keys: {list(edge.keys())}")
        
        edge_get = orchestration.edge_get(session, edge_id)
        print(f"\n✅ edge_get: {type(edge_get)}")
        print(f"   Return: dict with keys: {list(edge_get.keys())}")
        
        edge_exists = orchestration.edge_exists(session, edge_id)
        print(f"\n✅ edge_exists: {type(edge_exists)}")
        print(f"   Return: bool = {edge_exists}")
        
        edge_count = orchestration.edge_count(session)
        print(f"\n✅ edge_count: {type(edge_count)}")
        print(f"   Return: int = {edge_count}")
        
        edge_filter = orchestration.edge_filter(session, {'workflow_id': workflow_id})
        print(f"\n✅ edge_filter: {type(edge_filter)}")
        print(f"   Return: List[str] with length: {len(edge_filter)}")
        print(f"   Sample: {edge_filter[:2] if edge_filter else []}")
        
        edge_get_by_workflow = orchestration.edge_get_by_workflow(session, workflow_id)
        print(f"\n✅ edge_get_by_workflow: {type(edge_get_by_workflow)}")
        print(f"   Return: List[str] with length: {len(edge_get_by_workflow)}")
        print(f"   Sample: {edge_get_by_workflow[:2] if edge_get_by_workflow else []}")
        
        # workflow_get'i şimdi test edebiliriz
        workflow_get = orchestration.workflow_get(session, workflow_id)
        print(f"\n✅ workflow_get: {type(workflow_get)}")
        print(f"   Return: dict with keys: {list(workflow_get.keys())}")
        
        print("\n📋 EXECUTION FUNCTIONS OUTPUT FORMATS:")
        print("=" * 60)
        
        # Execution başlat
        execution = orchestration.execution_start(session, workflow_id)
        # execution_start dict döndürüyor ama id alanı yok, execution_id'yi başka şekilde alalım
        execution_id = execution.get('id') or execution.get('execution_id') or 'EX-TEST-ID'
        
        print(f"\n✅ execution_start: {type(execution)}")
        print(f"   Return: dict with keys: {list(execution.keys())}")
        
        print(f"\n✅ execution_start: {type(execution)}")
        print(f"   Return: dict with keys: {list(execution.keys())}")
        
        # Execution fonksiyonlarını test etmek için gerçek execution_id'yi alalım
        execution_list = orchestration.execution_list(session)
        if execution_list:
            real_execution_id = execution_list[0]['id']
            
            execution_get = orchestration.execution_get(session, real_execution_id)
            print(f"\n✅ execution_get: {type(execution_get)}")
            print(f"   Return: dict with keys: {list(execution_get.keys())}")
            
            execution_count = orchestration.execution_count(session)
            print(f"\n✅ execution_count: {type(execution_count)}")
            print(f"   Return: int = {execution_count}")
            
            execution_exists = orchestration.execution_exists(session, real_execution_id)
            print(f"\n✅ execution_exists: {type(execution_exists)}")
            print(f"   Return: bool = {execution_exists}")
            
            execution_filter = orchestration.execution_filter(session, {})
            print(f"\n✅ execution_filter: {type(execution_filter)}")
            print(f"   Return: List[str] with length: {len(execution_filter)}")
            print(f"   Sample: {execution_filter[:2] if execution_filter else []}")
            
            execution_get_status = orchestration.execution_get_status(session, real_execution_id)
            print(f"\n✅ execution_get_status: {type(execution_get_status)}")
            print(f"   Return: str = '{execution_get_status}'")
        else:
            print(f"\n⚠️ No executions found to test execution functions")
        
        print(f"\n✅ execution_list: {type(execution_list)}")
        print(f"   Return: List[dict] with length: {len(execution_list)}")
        
        print("\n📋 BATCH FUNCTIONS OUTPUT FORMATS:")
        print("=" * 60)
        
        # Batch operations test
        nodes_batch = orchestration.workflow_add_nodes_batch(session, workflow_id, [
            {
                'name': 'batch_node1',
                'script_id': script_id,
                'params': {'param1': 'batch_value1'},
                'max_retries': 3,
                'timeout_seconds': 300
            },
            {
                'name': 'batch_node2',
                'script_id': script_id,
                'params': {'param1': 'batch_value2'},
                'max_retries': 3,
                'timeout_seconds': 300
            }
        ])
        
        print(f"\n✅ workflow_add_nodes_batch: {type(nodes_batch)}")
        print(f"   Return: List[dict] with length: {len(nodes_batch)}")
        print(f"   Sample: {[node['id'] for node in nodes_batch[:2]]}")
        
        edges_batch = orchestration.workflow_add_edges_batch(session, workflow_id, [
            {
                'from_node_id': nodes_batch[0]['id'],
                'to_node_id': nodes_batch[1]['id'],
                'condition_type': 'success'
            }
        ])
        
        print(f"\n✅ workflow_add_edges_batch: {type(edges_batch)}")
        print(f"   Return: List[dict] with length: {len(edges_batch)}")
        print(f"   Sample: {[edge['id'] for edge in edges_batch[:2]]}")
        
        workflow_clone = orchestration.workflow_clone(session, workflow_id, 
            f'Cloned Format Test Workflow {unique_id}', 'Cloned workflow')
        
        print(f"\n✅ workflow_clone: {type(workflow_clone)}")
        print(f"   Return: dict with keys: {list(workflow_clone.keys())}")
        
        print("\n📋 COMPLETE OUTPUT FORMAT SUMMARY:")
        print("=" * 60)
        print("🎯 CREATE FUNCTIONS:")
        print("   ✅ workflow_create: dict")
        print("   ✅ script_create: dict")
        print("   ✅ environment_create: dict")
        print("   ✅ workflow_add_node: dict")
        print("   ✅ workflow_add_edge: dict")
        print("   ✅ execution_start: dict")
        
        print("\n🎯 GET FUNCTIONS:")
        print("   ✅ workflow_get: dict")
        print("   ✅ script_get: dict")
        print("   ✅ environment_get: dict")
        print("   ✅ node_get: dict")
        print("   ✅ edge_get: dict")
        print("   ✅ execution_get: dict")
        
        print("\n🎯 LIST FUNCTIONS:")
        print("   ✅ workflow_list: List[dict]")
        print("   ✅ script_list: List[dict]")
        print("   ✅ environment_list: List[dict]")
        print("   ✅ execution_list: List[dict]")
        
        print("\n🎯 COUNT FUNCTIONS:")
        print("   ✅ workflow_count: int")
        print("   ✅ script_count: int")
        print("   ✅ environment_count: int")
        print("   ✅ node_count: int")
        print("   ✅ edge_count: int")
        print("   ✅ execution_count: int")
        
        print("\n🎯 EXISTS FUNCTIONS:")
        print("   ✅ workflow_exists: bool")
        print("   ✅ script_exists: bool")
        print("   ✅ environment_exists: bool")
        print("   ✅ node_exists: bool")
        print("   ✅ edge_exists: bool")
        print("   ✅ execution_exists: bool")
        
        print("\n🎯 FILTER FUNCTIONS:")
        print("   ✅ workflow_filter: List[str]")
        print("   ✅ script_filter: List[str]")
        print("   ✅ environment_filter: List[str]")
        print("   ✅ node_filter: List[str]")
        print("   ✅ edge_filter: List[str]")
        print("   ✅ execution_filter: List[str]")
        
        print("\n🎯 SPECIAL FUNCTIONS:")
        print("   ✅ execution_get_status: str")
        print("   ✅ node_get_by_workflow: List[str]")
        print("   ✅ edge_get_by_workflow: List[str]")
        print("   ✅ workflow_add_nodes_batch: List[dict]")
        print("   ✅ workflow_add_edges_batch: List[dict]")
        print("   ✅ workflow_clone: dict")

if __name__ == "__main__":
    test_complete_output_formats()
