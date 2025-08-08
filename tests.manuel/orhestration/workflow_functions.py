"""
Manual tests for DatabaseOrchestration workflow functions
Run these tests manually to verify workflow operations
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from miniflow.database_manager.engine import DatabaseEngine
from miniflow.database_manager.config import get_sqlite_config
from miniflow.database_manager.orchestration import DatabaseOrchestration
from miniflow.database_manager.models import Base
from miniflow.exceptions import ValidationError, BusinessLogicError

def test_workflow_creation():
    """Test workflow creation with nodes and edges"""
    print("=== Testing Workflow Creation ===")
    
    config = get_sqlite_config(db_name='test_workflow.db')
    engine = DatabaseEngine(config)
    engine.create_tables(Base.metadata)  # Create tables if they don't exist
    orchestration = DatabaseOrchestration()
    
    with engine.get_session_context() as session:
        try:
            # Test 1: Single node workflow
            single_node_workflow = {
                "name": "Single Node Test",
                "description": "Test workflow with single node",
                "nodes": [
                    {
                        "name": "start_node",

                        "script_id": "SCR-001",
                        "params": {"input": "test"}
                    }
                ],
                "edges": []  # Single node doesn't need edges
            }
            
            result = orchestration.workflow_create(session, **single_node_workflow)
            print(f"✓ Single node workflow created: {result['workflow_id']}")
            
            # Test 2: Multi-node workflow with edges
            multi_node_workflow = {
                "name": "Multi Node Test",
                "description": "Test workflow with multiple nodes",
                "nodes": [
                    {
                        "name": "node_a",

                        "script_id": "SCR-001",
                        "params": {"input": "start"}
                    },
                    {
                        "name": "node_b", 

                        "script_id": "SCR-002",
                        "params": {"input": "middle"}
                    },
                    {
                        "name": "node_c",
 
                        "script_id": "SCR-003",
                        "params": {"input": "end"}
                    }
                ],
                "edges": [
                    {
                        "from_node": "node_a",
                        "to_node": "node_b",
                        "condition_type": "success"
                    },
                    {
                        "from_node": "node_b", 
                        "to_node": "node_c",
                        "condition_type": "success"
                    }
                ]
            }
            
            result = orchestration.workflow_create(session, **multi_node_workflow)
            print(f"✓ Multi-node workflow created: {result['workflow_id']}")
            print(f"  Nodes: {result['nodes']}")
            print(f"  Edges: {result['edges']}")
            
            # Test 3: Test validation - multi-node without edges should fail
            try:
                invalid_workflow = {
                    "name": "Invalid Workflow", 
                    "description": "Should fail validation",
                    "nodes": [
                        {"name": "node1", "node_type": "script", "script_id": "SCR-001"},
                        {"name": "node2", "node_type": "script", "script_id": "SCR-002"}
                    ],
                    "edges": []  # Missing edges for multi-node
                }
                orchestration.workflow_create(session, **invalid_workflow)
                print("✗ Validation failed - should have thrown error")
            except ValidationError as e:
                print(f"✓ Validation works: {e}")
                
            # session.commit() - handled by context manager
            
        except Exception as e:
            print(f"✗ Error: {e}")
            # session.rollback() - handled by context manager

def test_workflow_update():
    """Test workflow update functionality"""
    print("\n=== Testing Workflow Update ===")
    
    config = get_sqlite_config(db_name='test_workflow.db')
    engine = DatabaseEngine(config)
    engine.create_tables(Base.metadata)  # Create tables if they don't exist
    orchestration = DatabaseOrchestration()
    
    with engine.get_session_context() as session:
        try:
            # First create a workflow
            workflow_data = {
                "name": "Original Workflow",
                "description": "Original description",
                "nodes": [
                    {
                        "name": "original_node",

                        "script_id": "SCR-001",
                        "params": {"original": "param"}
                    }
                ],
                "edges": []
            }
            
            result = orchestration.workflow_create(session, **workflow_data)
            workflow_id = result['workflow_id']
            print(f"✓ Created workflow for update test: {workflow_id}")
            
            # Test update metadata only
            update_data = {
                "name": "Updated Workflow Name",
                "description": "Updated description"
            }
            
            updated = orchestration.workflow_update(session, workflow_id, **update_data)
            print(f"✓ Updated workflow metadata: {updated['workflow_id']}")
            
            # Test update with new nodes
            update_with_nodes = {
                "name": "Updated with Nodes",
                "nodes": [
                    {
                        "name": "original_node",  # Keep existing
 
                        "script_id": "SCR-001",
                        "params": {"updated": "param"}
                    },
                    {
                        "name": "new_node",  # Add new

                        "script_id": "SCR-002", 
                        "params": {"new": "param"}
                    }
                ],
                "edges": [
                    {
                        "from_node": "original_node",
                        "to_node": "new_node",
                        "condition_type": "success"
                    }
                ]
            }
            
            updated = orchestration.workflow_update(session, workflow_id, **update_with_nodes)
            print(f"✓ Updated workflow with new nodes: {len(updated['nodes'])} nodes")
            
            # session.commit() - handled by context manager
            
        except Exception as e:
            print(f"✗ Error: {e}")
            # session.rollback() - handled by context manager

def test_workflow_get_and_list():
    """Test workflow retrieval functions"""
    print("\n=== Testing Workflow Get and List ===")
    
    config = get_sqlite_config(db_name='test_workflow.db')
    engine = DatabaseEngine(config)
    engine.create_tables(Base.metadata)  # Create tables if they don't exist
    orchestration = DatabaseOrchestration()
    
    with engine.get_session_context() as session:
        try:
            # Get single workflow with details
            workflows = orchestration.workflow_list(session, include_detail=False)
            if workflows:
                workflow_id = workflows[0]['id']
                
                # Get with details
                detailed = orchestration.workflow_get(session, workflow_id, include_detail=True)
                print(f"✓ Got workflow with details: {detailed['name']}")
                print(f"  Nodes: {len(detailed['nodes'])}")
                print(f"  Edges: {len(detailed['edges'])}")
                
                # Get without details
                basic = orchestration.workflow_get(session, workflow_id, include_detail=False) 
                print(f"✓ Got workflow without details: {basic['name']}")
                print(f"  Nodes: {len(basic['nodes'])}")
                print(f"  Edges: {len(basic['edges'])}")
            
            # List all workflows
            all_workflows = orchestration.workflow_list(session, include_detail=True)
            print(f"✓ Listed {len(all_workflows)} workflows with details")
            
            basic_list = orchestration.workflow_list(session, include_detail=False)
            print(f"✓ Listed {len(basic_list)} workflows without details")
            
            # Test count and exists
            count = orchestration.workflow_count(session)
            print(f"✓ Total workflow count: {count}")
            
            if workflows:
                exists = orchestration.workflow_exists(session, workflows[0]['id'])
                print(f"✓ Workflow exists check: {exists}")
                
        except Exception as e:
            print(f"✗ Error: {e}")

def test_workflow_delete():
    """Test workflow deletion with cascade"""
    print("\n=== Testing Workflow Delete ===")
    
    config = get_sqlite_config(db_name='test_workflow.db')
    engine = DatabaseEngine(config)
    engine.create_tables(Base.metadata)  # Create tables if they don't exist
    orchestration = DatabaseOrchestration()
    
    with engine.get_session_context() as session:
        try:
            # Create a workflow to delete
            workflow_data = {
                "name": "Delete Test Workflow",
                "description": "Will be deleted",
                "nodes": [
                    {
                        "name": "delete_node",

                        "script_id": "SCR-001"
                    }
                ],
                "edges": []
            }
            
            result = orchestration.workflow_create(session, **workflow_data)
            workflow_id = result['workflow_id']
            print(f"✓ Created workflow to delete: {workflow_id}")
            
            # Verify it exists
            exists_before = orchestration.workflow_exists(session, workflow_id)
            print(f"✓ Workflow exists before delete: {exists_before}")
            
            # Delete it
            deleted = orchestration.workflow_delete(session, workflow_id)
            print(f"✓ Deleted workflow: {deleted['id']}")
            
            # Verify it's gone
            exists_after = orchestration.workflow_exists(session, workflow_id)
            print(f"✓ Workflow exists after delete: {exists_after}")
            
            # Test deleting non-existent workflow
            try:
                orchestration.workflow_delete(session, "INVALID-ID")
                print("✗ Should have failed for invalid ID")
            except BusinessLogicError as e:
                print(f"✓ Correctly failed for invalid ID: {e}")
                
            # session.commit() - handled by context manager
            
        except Exception as e:
            print(f"✗ Error: {e}")
            # session.rollback() - handled by context manager

def test_workflow_filter():
    """Test workflow filtering"""
    print("\n=== Testing Workflow Filter ===")
    
    config = get_sqlite_config(db_name='test_workflow.db')
    engine = DatabaseEngine(config)
    engine.create_tables(Base.metadata)  # Create tables if they don't exist
    orchestration = DatabaseOrchestration()
    
    with engine.get_session_context() as session:
        try:
            # Create workflows with different names for filtering
            test_workflows = [
                {
                    "name": "Filter Test Alpha",
                    "description": "Alpha workflow",
                    "nodes": [{"name": "alpha_node", "node_type": "script", "script_id": "SCR-001"}],
                    "edges": []
                },
                {
                    "name": "Filter Test Beta", 
                    "description": "Beta workflow",
                    "nodes": [{"name": "beta_node", "node_type": "script", "script_id": "SCR-002"}],
                    "edges": []
                }
            ]
            
            created_ids = []
            for wf_data in test_workflows:
                result = orchestration.workflow_create(session, **wf_data)
                created_ids.append(result['workflow_id'])
                print(f"✓ Created test workflow: {result['workflow_id']}")
            
            # Test filtering by name pattern
            alpha_filters = {'name': 'Filter Test Alpha'}
            alpha_results = orchestration.workflow_filter(session, alpha_filters)
            print(f"✓ Filtered Alpha workflows: {len(alpha_results)}")
            
            # Filter by description
            beta_filters = {'description': 'Beta workflow'}
            beta_results = orchestration.workflow_filter(session, beta_filters)
            print(f"✓ Filtered Beta workflows: {len(beta_results)}")
            
            # session.commit() - handled by context manager
            
        except Exception as e:
            print(f"✗ Error: {e}")
            # session.rollback() - handled by context manager

def run_all_workflow_tests():
    """Run all workflow tests"""
    print("Starting Workflow Function Tests")
    print("=" * 50)
    
    test_workflow_creation()
    test_workflow_update()
    test_workflow_get_and_list()
    test_workflow_delete()
    test_workflow_filter()
    
    print("\n" + "=" * 50)
    print("Workflow tests completed!")

if __name__ == "__main__":
    run_all_workflow_tests()
