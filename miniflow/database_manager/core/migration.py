"""
Database migration and initialization utilities
"""
from sqlalchemy import Index, text
from sqlalchemy.exc import SQLAlchemyError
from ..models import Base
# TEMPORARY: Direct import instead of get_database_manager (circular import issue)
# from .manager import get_database_manager


def create_all_tables(manager):
    """Create all tables in the database using the provided manager"""
    try:
        Base.metadata.create_all(manager.engine)
        return True
    except SQLAlchemyError as e:
        print(f"Error creating tables: {e}")
        return False


def drop_all_tables(manager):
    """Drop all tables in the database using the provided manager"""
    try:
        Base.metadata.drop_all(manager.engine)
        return True
    except SQLAlchemyError as e:
        print(f"Error dropping tables: {e}")
        return False


def _create_performance_indexes(engine):
    """Create performance indexes manually"""
    
    indexes = [
        # Workflows indexes
        Index('idx_workflows_status', 'workflows.status'),
        
        # Nodes indexes
        Index('idx_nodes_workflow_id', 'nodes.workflow_id'),
        
        # Edges indexes
        Index('idx_edges_workflow_id', 'edges.workflow_id'),
        Index('idx_edges_from_node', 'edges.from_node_id'),
        Index('idx_edges_to_node', 'edges.to_node_id'),
        
        # Executions indexes
        Index('idx_executions_workflow_id', 'executions.workflow_id'),
        Index('idx_executions_status', 'executions.status'),
        
        # Execution Inputs indexes (eski execution_queue)
        Index('idx_execution_inputs_execution_id', 'execution_inputs.execution_id'),
        Index('idx_execution_inputs_status_priority', 'execution_inputs.status', 'execution_inputs.priority'),
        
        # Execution Outputs indexes (eski execution_results)
        Index('idx_execution_outputs_execution_id', 'execution_outputs.execution_id'),
        Index('idx_execution_outputs_node_id', 'execution_outputs.node_id'),
        
        # Triggers indexes
        Index('idx_triggers_workflow_id', 'triggers.workflow_id'),
    ]
    
    # Create indexes
    for index in indexes:
        try:
            index.create(engine, checkfirst=True)
        except Exception as e:
            print(f"Warning: Could not create index {index.name}: {e}")


def init_database(manager):
    """Initialize database with all tables using the provided manager"""
    return create_all_tables(manager) 