from typing import List, Dict, Any, Optional
from ..repositories import WorkflowRepository, NodeRepository, EdgeRepository, TriggerRepository
from ..models import Workflow, Node, Edge


class WorkflowService:
    """Service for workflow business logic"""
    
    def __init__(self):
        self.workflow_repo = WorkflowRepository()
        self.node_repo = NodeRepository()
        self.edge_repo = EdgeRepository()
        self.trigger_repo = TriggerRepository()
    
    def create_workflow_from_json(self, workflow_data: Dict[str, Any]) -> Workflow:
        """Create workflow with nodes and edges from JSON data"""
        # Create workflow
        workflow = self.workflow_repo.create(
            name=workflow_data['name'],
            description=workflow_data.get('description', ''),
            status='inactive',
            config=str(workflow_data.get('config', {}))
        )
        
        # Create nodes
        nodes_map = {}
        for node_data in workflow_data.get('nodes', []):
            node = self.node_repo.create(
                workflow_id=workflow.id,
                name=node_data['name'],
                type=node_data.get('type', 'task'),
                config=str(node_data.get('config', {}))
            )
            nodes_map[node_data['name']] = node
        
        # Create edges
        for edge_data in workflow_data.get('edges', []):
            from_node = nodes_map.get(edge_data['from'])
            to_node = nodes_map.get(edge_data['to'])
            
            if from_node and to_node:
                self.edge_repo.create(
                    workflow_id=workflow.id,
                    from_node_id=from_node.id,
                    to_node_id=to_node.id,
                    condition=edge_data.get('condition', '')
                )
        
        return workflow
    
    def get_workflow_structure(self, workflow_id: str) -> Dict[str, Any]:
        """Get complete workflow structure with nodes and edges"""
        workflow = self.workflow_repo.get_by_id(workflow_id)
        if not workflow:
            return None
        
        nodes = self.node_repo.get_by_workflow(workflow_id)
        edges = self.edge_repo.get_by_workflow(workflow_id)
        
        return {
            'workflow': workflow,
            'nodes': nodes,
            'edges': edges
        }
    
    def validate_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Validate workflow structure"""
        structure = self.get_workflow_structure(workflow_id)
        if not structure:
            return {'valid': False, 'errors': ['Workflow not found']}
        
        errors = []
        nodes = structure['nodes']
        edges = structure['edges']
        
        # Check for orphaned nodes
        node_ids = {node.id for node in nodes}
        for edge in edges:
            if edge.from_node_id not in node_ids:
                errors.append(f"Edge references non-existent from_node: {edge.from_node_id}")
            if edge.to_node_id not in node_ids: 
                errors.append(f"Edge references non-existent to_node: {edge.to_node_id}")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'stats': {
                'node_count': len(nodes),
                'edge_count': len(edges)
            }
        }
    
    def delete_workflow_cascade(self, workflow_id: str) -> bool:
        """Delete workflow and all related data"""
        # Delete in order: edges -> nodes -> workflow
        self.edge_repo.delete_by_workflow(workflow_id)
        self.node_repo.delete_by_workflow(workflow_id)
        return self.workflow_repo.delete(workflow_id) 