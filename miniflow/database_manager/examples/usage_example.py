"""
Database Manager Usage Example
Demonstrates how to use the new ORM-based database system
"""
import uuid
import json
from miniflow.database_manager.core import (
    DatabaseConfig, DatabaseType, set_database_manager, 
    get_database_manager, init_database
)
from miniflow.database_manager.models import (
    Workflow, Node, Edge, Execution, ExecutionInput, 
    ExecutionOutput, Trigger
)


def setup_database():
    """Setup database connection"""
    config = DatabaseConfig(
        url="sqlite:///miniflow_new.db",
        db_type=DatabaseType.SQLITE,
        pool_size=5,
        echo=True  # Enable SQL logging for demo
    )
    
    # Initialize database manager
    manager = set_database_manager(config)
    
    # Create tables
    init_database()
    
    return manager


def create_sample_workflow():
    """Create a sample workflow with nodes and edges"""
    manager = get_database_manager()
    
    with manager.get_session() as session:
        # Create workflow
        workflow = Workflow(
            id=str(uuid.uuid4()),
            name="Sample Data Processing",
            description="A sample workflow for data processing",
            status="active",
            version=1
        )
        session.add(workflow)
        
        # Create nodes
        node1 = Node(
            id=str(uuid.uuid4()),
            workflow_id=workflow.id,
            name="Load Data",
            type="python",
            script="load_data.py",
            params=json.dumps({
                "input_file": "/data/input.csv",
                "format": "csv",
                "encoding": "utf-8"
            })
        )
        
        node2 = Node(
            id=str(uuid.uuid4()),
            workflow_id=workflow.id,
            name="Process Data",
            type="python",
            script="process_data.py",
            params=json.dumps({
                "algorithm": "transform",
                "output_format": "json"
            })
        )
        
        node3 = Node(
            id=str(uuid.uuid4()),
            workflow_id=workflow.id,
            name="Save Results",
            type="python",
            script="save_results.py",
            params=json.dumps({
                "output_path": "/data/output/",
                "compress": True
            })
        )
        
        session.add_all([node1, node2, node3])
        
        # Create edges (workflow connections)
        edge1 = Edge(
            id=str(uuid.uuid4()),
            workflow_id=workflow.id,
            from_node_id=node1.id,
            to_node_id=node2.id,
            condition_type="success"
        )
        
        edge2 = Edge(
            id=str(uuid.uuid4()),
            workflow_id=workflow.id,
            from_node_id=node2.id,
            to_node_id=node3.id,
            condition_type="success"
        )
        
        session.add_all([edge1, edge2])
        
        # Create trigger
        trigger = Trigger(
            id=str(uuid.uuid4()),
            workflow_id=workflow.id,
            trigger_type="schedule",
            config=json.dumps({
                "schedule": "0 9 * * 1-5",  # Weekdays at 9 AM
                "timezone": "UTC"
            }),
            is_active=1
        )
        
        session.add(trigger)
        
        # Commit all changes
        session.commit()
        
        return workflow.id


def create_execution_example(workflow_id):
    """Create an execution example"""
    manager = get_database_manager()
    
    with manager.get_session() as session:
        # Create execution
        execution = Execution(
            id=str(uuid.uuid4()),
            workflow_id=workflow_id,
            status="running",
            results=json.dumps({"status": "started"})
        )
        
        session.add(execution)
        
        # Get workflow nodes
        nodes = session.query(Node).filter(Node.workflow_id == workflow_id).all()
        
        # Create execution inputs (eski queue items)
        for i, node in enumerate(nodes):
            execution_input = ExecutionInput(
                id=str(uuid.uuid4()),
                execution_id=execution.id,
                node_id=node.id,
                status="pending" if i > 0 else "ready",
                priority=i,
                dependency_count=i
            )
            session.add(execution_input)
            
            # Create sample output for first node
            if i == 0:
                execution_output = ExecutionOutput(
                    id=str(uuid.uuid4()),
                    execution_id=execution.id,
                    node_id=node.id,
                    status="success",
                    result_data=json.dumps({
                        "records_loaded": 1000,
                        "processing_time": 45.2,
                        "output_file": "/tmp/processed_data.json"
                    })
                )
                session.add(execution_output)
        
        session.commit()
        return execution.id


def query_examples():
    """Show various query examples"""
    manager = get_database_manager()
    
    with manager.get_session() as session:
        print("=== Query Examples ===")
        
        # 1. Get all active workflows
        workflows = session.query(Workflow).filter(Workflow.status == 'active').all()
        print(f"Active workflows: {len(workflows)}")
        for wf in workflows:
            print(f"  - {wf.name} (v{wf.version})")
        
        # 2. Get workflow with its nodes
        if workflows:
            wf = workflows[0]
            print(f"\nNodes in workflow '{wf.name}':")
            for node in wf.nodes:
                params = json.loads(node.params) if node.params else {}
                print(f"  - {node.name} ({node.type})")
                print(f"    Params: {params}")
        
        # 3. Get workflow connections
            print(f"\nConnections in workflow '{wf.name}':")
            for edge in wf.edges:
                from_node = session.query(Node).filter(Node.id == edge.from_node_id).first()
                to_node = session.query(Node).filter(Node.id == edge.to_node_id).first()
                print(f"  - {from_node.name} -> {to_node.name} (on {edge.condition_type})")
        
        # 4. Get executions
        executions = session.query(Execution).all()
        print(f"\nExecutions: {len(executions)}")
        for exec in executions:
            print(f"  - {exec.id} ({exec.status})")
            print(f"    Input items: {len(exec.execution_inputs)}")
            print(f"    Output items: {len(exec.execution_outputs)}")


def main():
    """Main demo function"""
    print("🚀 Database Manager Demo")
    print("=" * 50)
    
    # Setup
    print("1. Setting up database...")
    manager = setup_database()
    print(f"   ✅ Database manager initialized")
    print(f"   ✅ Health status: {manager.is_healthy()}")
    
    # Create sample data
    print("\n2. Creating sample workflow...")
    workflow_id = create_sample_workflow()
    print(f"   ✅ Workflow created: {workflow_id}")
    
    print("\n3. Creating execution example...")
    execution_id = create_execution_example(workflow_id)
    print(f"   ✅ Execution created: {execution_id}")
    
    # Query examples
    print("\n4. Running query examples...")
    query_examples()
    
    # Cleanup
    print("\n5. Cleanup...")
    manager.shutdown()
    print("   ✅ Database manager shutdown")
    
    print("\n🎉 Demo completed successfully!")


if __name__ == "__main__":
    main() 