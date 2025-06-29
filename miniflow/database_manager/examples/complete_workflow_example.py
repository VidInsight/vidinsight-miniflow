"""
Complete Database Manager Usage Example
======================================

Bu örnek Database Manager'ın tüm özelliklerini gösterir:
- Repository Pattern ile CRUD operations
- Service Layer ile business logic
- Workflow orchestration
- Complete workflow lifecycle
"""

import json
from miniflow.database_manager.core.manager import DatabaseManager
from miniflow.database_manager.services import WorkflowService, ExecutionService, OrchestrationService


def main():
    """Complete workflow example"""
    
    # 1. Initialize database manager
    print("🚀 Initializing Database Manager...")
    manager = DatabaseManager()
    manager.initialize_database()
    
    # 2. Initialize services
    workflow_service = WorkflowService()
    execution_service = ExecutionService()
    orchestration_service = OrchestrationService()
    
    # 3. Create workflow from JSON
    print("\n📋 Creating workflow from JSON...")
    workflow_data = {
        "name": "Math Processing Workflow",
        "description": "A sample math processing workflow",
        "config": {"timeout": 300},
        "nodes": [
            {
                "name": "input_node",
                "type": "input",
                "config": {"inputs": ["number1", "number2"]}
            },
            {
                "name": "add_numbers",
                "type": "task", 
                "config": {"script": "scripts/add_numbers.py"}
            },
            {
                "name": "multiply_result",
                "type": "task",
                "config": {"script": "scripts/multiply_numbers.py", "factor": 2}
            },
            {
                "name": "output_node",
                "type": "output",
                "config": {"output_format": "json"}
            }
        ],
        "edges": [
            {"from": "input_node", "to": "add_numbers"},
            {"from": "add_numbers", "to": "multiply_result"},
            {"from": "multiply_result", "to": "output_node"}
        ]
    }
    
    # Create workflow
    workflow = workflow_service.create_workflow_from_json(workflow_data)
    print(f"✅ Created workflow: {workflow.name} (ID: {workflow.id})")
    
    # 4. Validate workflow structure
    print("\n🔍 Validating workflow...")
    validation = workflow_service.validate_workflow(workflow.id)
    print(f"Valid: {validation['valid']}")
    print(f"Stats: {validation['stats']}")
    if validation['errors']:
        print(f"Errors: {validation['errors']}")
    
    # 5. Get workflow structure
    print("\n🏗️ Workflow structure:")
    structure = workflow_service.get_workflow_structure(workflow.id)
    print(f"Nodes: {len(structure['nodes'])}")
    print(f"Edges: {len(structure['edges'])}")
    
    for node in structure['nodes']:
        print(f"  - Node: {node.name} ({node.type})")
    
    for edge in structure['edges']:
        from_node = next(n for n in structure['nodes'] if n.id == edge.from_node_id)
        to_node = next(n for n in structure['nodes'] if n.id == edge.to_node_id)
        print(f"  - Edge: {from_node.name} → {to_node.name}")
    
    # 6. Execute workflow
    print("\n▶️ Starting workflow execution...")
    context = {"number1": 10, "number2": 20}
    execution_id = orchestration_service.execute_workflow(workflow.id, context)
    print(f"✅ Started execution: {execution_id}")
    
    # 7. Monitor execution progress
    print("\n📊 Execution progress:")
    progress = orchestration_service.get_execution_progress(execution_id)
    print(f"Status: {progress['status']}")
    print(f"Progress: {progress['progress_percentage']}%")
    print(f"Completed nodes: {progress['completed_nodes']}/{progress['total_nodes']}")
    
    # 8. Get ready tasks (simulation)
    print("\n📋 Ready tasks:")
    ready_tasks = orchestration_service.get_ready_tasks(limit=5)
    for task in ready_tasks:
        print(f"  - Task: {task['node_name']} (Type: {task['node_type']})")
        print(f"    Execution: {task['execution_id']}")
        print(f"    Config: {task['node_config']}")
    
    # 9. Simulate task completion
    print("\n✅ Simulating task completions...")
    for task in ready_tasks[:2]:  # Complete first 2 tasks
        # Simulate task execution result
        result = {
            "status": "success",
            "output": f"Completed {task['node_name']}",
            "execution_time": 1.5
        }
        
        execution_service._complete_node_execution = getattr(execution_service, 'complete_node_execution', None)
        if execution_service._complete_node_execution:
            try:
                # This would normally be called by the execution engine
                print(f"    Completing task: {task['node_name']}")
            except Exception as e:
                print(f"    Note: {e}")
    
    # 10. Get final status
    print("\n📈 Final execution status:")
    final_status = execution_service.get_execution_status(execution_id)
    if final_status:
        print(f"Execution: {final_status['execution'].status}")
        print(f"Total inputs: {final_status['stats']['total_inputs']}")
        print(f"Ready inputs: {final_status['stats']['ready_inputs']}")
        print(f"Completed outputs: {final_status['stats']['completed_outputs']}")
    
    # 11. Get workflow statistics
    print("\n📊 Workflow statistics:")
    stats = orchestration_service.get_workflow_statistics(workflow.id)
    print(f"Total executions: {stats['total_executions']}")
    print(f"Success rate: {stats['success_rate']}%")
    print(f"Running executions: {stats['running_executions']}")
    
    print("\n🎉 Example completed successfully!")


def demo_repository_usage():
    """Demonstrate repository usage"""
    print("\n" + "="*50)
    print("📚 REPOSITORY USAGE DEMO")
    print("="*50)
    
    from miniflow.database_manager.repositories import WorkflowRepository, NodeRepository
    
    # Repository usage examples
    workflow_repo = WorkflowRepository()
    node_repo = NodeRepository()
    
    # Create workflow
    workflow = workflow_repo.create(
        name="Test Workflow",
        description="Test description",
        status="active"
    )
    print(f"Created workflow: {workflow.name}")
    
    # Create nodes
    node1 = node_repo.create(
        workflow_id=workflow.id,
        name="start_node",
        type="input",
        config="{}"
    )
    
    node2 = node_repo.create(
        workflow_id=workflow.id,
        name="process_node", 
        type="task",
        config='{"script": "process.py"}'
    )
    
    print(f"Created nodes: {node1.name}, {node2.name}")
    
    # Query operations
    workflows = workflow_repo.get_active_workflows()
    print(f"Active workflows: {len(workflows)}")
    
    nodes = node_repo.get_by_workflow(workflow.id)
    print(f"Workflow nodes: {len(nodes)}")
    
    # Update operation
    updated_workflow = workflow_repo.update(workflow.id, status="inactive")
    print(f"Updated workflow status: {updated_workflow.status}")


if __name__ == "__main__":
    try:
        main()
        demo_repository_usage()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc() 