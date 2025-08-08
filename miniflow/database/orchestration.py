from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import Dict, Any, List

from .crud import (WorkflowCRUD, NodeCRUD, EdgeCRUD, ScriptCRUD, ArchivedExecutionCRUD,
                   ExecutionCRUD, ExecutionInputCRUD, ExecutionOutputCRUD, AuditLogCRUD, EnvironmentVariableCRUD)
from ..exceptions import ValidationError, BusinessLogicError



class DatabaseOrchestration:
    def __init__(self):
        self.workflow_crud = WorkflowCRUD()
        self.node_crud = NodeCRUD()
        self.edge_crud = EdgeCRUD()
        self.script_crud = ScriptCRUD()
        self.execution_crud = ExecutionCRUD()
        self.execution_input_crud = ExecutionInputCRUD()
        self.execution_output_crud = ExecutionOutputCRUD()
        self.archived_execution_crud = ArchivedExecutionCRUD()
        self.environment_crud = EnvironmentVariableCRUD()  # Assuming EnvironmentCRUD is defined elsewhere
        self.audit_log_crud = AuditLogCRUD()

    @staticmethod
    def _resolve_node_reference(node_ref: str, node_ids_map: dict) -> str:
        """
        Resolve node reference to ID.
        
        Args:
            node_ref: Either node name or node ID (starting with 'ND-')
            node_ids_map: Dictionary mapping node names to IDs
            
        Returns:
            Node ID string
            
        Raises:
            ValidationError: If node reference cannot be resolved
        """
        # If it's already an ID (starts with 'ND-'), return as-is
        if node_ref.startswith('ND-'):
            return node_ref
            
        # Otherwise, it's a name - look up in the mapping
        if node_ref in node_ids_map:
            return node_ids_map[node_ref]
            
        # If not found, raise error
        raise ValidationError(f"Node reference '{node_ref}' not found. Available nodes: {list(node_ids_map.keys())}")

    def _combine_execution_results(self, session: Session, execution_id: str) -> Dict[str, Any]:
        """
        Combine execution results from all nodes in a workflow execution.
        """
        execution = self.execution_crud.find_by_id(session, execution_id)
        workflow = self.workflow_crud.find_by_id(session, execution.workflow_id)

        wf_nodes = self.node_crud.filter(session, {'workflow_id': workflow.id})
        wf_node_ids = {node.id for node in wf_nodes}

        ex_nodes = self.execution_output_crud.filter(session, {'execution_id': execution.id})

        # Calculate progress statistics
        progress = {
            'total': len(wf_nodes),
            'success': 0,
            'failure': 0,
            'cancelled': 0,
            'timeout': 0
        }
        
        
        for ex_node in ex_nodes:
            if hasattr(ex_node.status, 'value'):
                status_val = ex_node.status.value.lower()
            else:
                status_val = str(ex_node.status).lower()
                
            if status_val == 'success':
                progress['success'] += 1
            elif status_val == 'failure':
                progress['failure'] += 1
            elif status_val == 'cancelled':
                progress['cancelled'] += 1
            elif status_val == 'timeout':
                progress['timeout'] += 1
        
        # Calculate cancelled nodes: difference between total execution outputs and valid nodes
        cancelled_from_invalid_nodes = len(ex_nodes) - len(wf_nodes)
        progress['cancelled'] += cancelled_from_invalid_nodes

        combined_results = {
            'execution_id': execution_id,
            'workflow_id': execution.workflow_id,
            'execution_status': execution.status.value if hasattr(execution.status, 'value') else str(execution.status),
            'started_at': execution.started_at.isoformat() if execution.started_at else None,
            'ended_at': execution.ended_at.isoformat() if execution.ended_at else None,
            'total_duration_seconds': (
                (execution.ended_at - execution.started_at).total_seconds()
                if execution.ended_at and execution.started_at else None
            ),
            'summary': {
                'total_nodes': progress['total'],
                'successful_nodes': progress['success'],
                'failed_nodes': progress['failure'],
                'cancelled_nodes': progress['cancelled'],
                'timeout_nodes': progress['timeout'],
                'success_rate': (
                    (progress['success'] / progress['total'] * 100)
                    if progress['total'] > 0 else 0
                )
            },
            'node_results': {}
        }
        
        # Add results for each executed node
        for exec_node_payload in ex_nodes:
            if exec_node_payload.node_id in wf_node_ids:
                # Get node details for valid workflow nodes
                node = self.node_crud.find_by_id(session, exec_node_payload.node_id)
                node_name = node.name if node else f"{exec_node_payload.node_id}"
                
                payload = {
                    'status': exec_node_payload.status.value if hasattr(exec_node_payload.status, 'value') else str(exec_node_payload.status),
                    'result_data': exec_node_payload.result_data or {},
                    'started_at': exec_node_payload.started_at.isoformat() if exec_node_payload.started_at else None,
                    'ended_at': exec_node_payload.ended_at.isoformat() if exec_node_payload.ended_at else None,
                    'duration_seconds': (
                        (exec_node_payload.ended_at - exec_node_payload.started_at).total_seconds()
                        if exec_node_payload.ended_at and exec_node_payload.started_at else None
                    )
                }
                combined_results['node_results'][node_name] = payload
            else:
                # Node ID not found in current workflow - mark as cancelled
                node_name = f"cancelled_node_{exec_node_payload.node_id}"
                payload = {
                    'status': 'cancelled',
                    'result_data': {'reason': 'Node has been cancelled'},
                }
                combined_results['node_results'][node_name] = payload
        
        # Add placeholder entries for nodes that haven't executed yet
        executed_node_ids = {ex_node.node_id for ex_node in ex_nodes}
        for node in wf_nodes:
            if node.id not in executed_node_ids:
                combined_results['node_results'][node.name] = {
                    'status': 'pending',
                    'result_data': {},
                    'started_at': None,
                    'ended_at': None,
                    'duration_seconds': None
                }
        
        return combined_results
        
    # ============================================================================================ WORKFLOW FUNCTIONS ==
    def workflow_load(self, session: Session, **workflow_data):
        """Create a new workflow."""

        workflow_payload = {
            'name': workflow_data.get('name'),
            'description': workflow_data.get('description'),
        }

        workflow = self.workflow_crud.create_workflow(session=session, **workflow_payload)

        wf_nodes = workflow_data.get("nodes", [])
        if not wf_nodes:
            raise ValidationError("Workflow must have at least one node.")

        wf_node_ids = {}
        for idx, node_payload in enumerate(wf_nodes):
            # Create node with workflow_id
            node_data = {**node_payload, 'workflow_id': workflow.id}
            node = self.node_crud.create_node(session=session, **node_data)
            wf_node_ids[node.name] = node.id

        wf_edges = workflow_data.get("edges", [])
        # Multi-node workflows require at least one edge, single-node workflows don't need edges
        if len(wf_nodes) > 1 and not wf_edges:
            raise ValidationError("Multi-node workflow must have at least one edge.")

        wf_edge_ids = []
        for idx, edge_payload in enumerate(wf_edges):
            # Resolve node references (supports both names and IDs)
            from_node_id = self._resolve_node_reference(edge_payload['from_node'], wf_node_ids)
            to_node_id = self._resolve_node_reference(edge_payload['to_node'], wf_node_ids)
            
            edge_data = {
                'from_node_id': from_node_id,
                'to_node_id': to_node_id,
                'workflow_id': workflow.id,
                'condition_type': edge_payload.get('condition_type', 'success')
            }
            
            edge = self.edge_crud.create_edge(session=session, **edge_data)
            wf_edge_ids.append(edge.id)

        return {
            "workflow_id": workflow.id,
            'created_at': workflow.created_at.isoformat() if workflow.created_at else None,
            'nodes': wf_node_ids,
            'edges': wf_edge_ids,
        }

    def workflow_delete(self, session: Session, workflow_id: str):
        """Delete a workflow and its associated nodes and edges using CASCADE DELETE."""
        
        # First verify workflow exists
        if not self.workflow_crud.exists(session, workflow_id):
            raise BusinessLogicError(f"Workflow with ID {workflow_id} not found.")

        # SQLAlchemy CASCADE DELETE handles all related records automatically
        # This single delete will remove: nodes, edges, executions, execution_inputs, execution_outputs
        workflow = self.workflow_crud.delete(session, workflow_id)

        return workflow.to_dict()

    def workflow_update(self, session: Session, workflow_id: str, **workflow_data):
        # First verify workflow exists
        if not self.workflow_crud.exists(session, workflow_id):
            raise BusinessLogicError(f"Workflow with ID {workflow_id} not found.")
            
        workflow_payload = {
            'name': workflow_data.get('name'),
            'description': workflow_data.get('description'),
        }
        # Remove None values to avoid overwriting with None
        workflow_payload = {k: v for k, v in workflow_payload.items() if v is not None}

        workflow = self.workflow_crud.update_workflow(session, workflow_id, **workflow_payload)

        wf_nodes = workflow_data.get("nodes", [])
        if not wf_nodes:
            # If no nodes provided, don't update nodes - just update workflow metadata
            return {
                "workflow_id": workflow.id,
                'created_at': workflow.created_at.isoformat() if workflow.created_at else None,
                'nodes': {},
                'edges': [],
            }

        # For update, we need to handle existing nodes properly
        # This is a simplified approach - in production you might want more sophisticated merge logic
        existing_nodes = self.node_crud.filter(session, {'workflow_id': workflow_id})
        existing_node_map = {node.name: node.id for node in existing_nodes}
        
        wf_node_ids = {}
        for idx, node_payload in enumerate(wf_nodes):
            node_name = node_payload.get('name')
            node_data = {**node_payload, 'workflow_id': workflow.id}
            
            if node_name in existing_node_map:
                # Update existing node
                node_id = existing_node_map[node_name]
                node = self.node_crud.update_node(session=session, node_id=node_id, **node_data)
                wf_node_ids[node.name] = node.id
            else:
                # Create new node
                node = self.node_crud.create_node(session=session, **node_data)
                wf_node_ids[node.name] = node.id

        wf_edges = workflow_data.get("edges", [])
        # Multi-node workflows require at least one edge, single-node workflows don't need edges
        if len(wf_nodes) > 1 and not wf_edges:
            raise ValidationError("Multi-node workflow must have at least one edge.")
        
        # Remove existing edges for this workflow to avoid conflicts
        existing_edges = self.edge_crud.filter(session, {'workflow_id': workflow_id})
        for edge in existing_edges:
            self.edge_crud.delete(session, edge.id)
        
        wf_edge_ids = []
        for idx, edge_payload in enumerate(wf_edges):
            # Resolve node references (supports both names and IDs)
            from_node_id = self._resolve_node_reference(edge_payload['from_node'], wf_node_ids)
            to_node_id = self._resolve_node_reference(edge_payload['to_node'], wf_node_ids)
            
            edge_data = {
                'from_node_id': from_node_id,
                'to_node_id': to_node_id,
                'workflow_id': workflow.id,
                'condition_type': edge_payload.get('condition_type', 'success')
            }
            
            edge = self.edge_crud.create_edge(session=session, **edge_data)
            wf_edge_ids.append(edge.id)

        return {
            "workflow_id": workflow.id,
            'created_at': workflow.created_at.isoformat() if workflow.created_at else None,
            'nodes': wf_node_ids,
            'edges': wf_edge_ids,
        }

    def workflow_get(self, session: Session, workflow_id: str, include_detail: bool = True):
        """Get a workflow by ID."""
        
        # First verify workflow exists
        workflow = self.workflow_crud.find_by_id(session, workflow_id)
        if not workflow:
            raise BusinessLogicError(f"Workflow with ID {workflow_id} not found.")

        wf_payload = workflow.to_dict()
        
        if include_detail:
            # Include nodes and edges (default behavior for single workflow get)
            wf_nodes = self.node_crud.filter(session, {'workflow_id': workflow_id})
            if not wf_nodes:
                raise BusinessLogicError("Workflow must have at least one node.")

            wf_edges = self.edge_crud.filter(session, {'workflow_id': workflow_id})
            # Single-node workflows don't require edges, multi-node workflows do
            if len(wf_nodes) > 1 and not wf_edges:
                raise BusinessLogicError("Multi-node workflow must have at least one edge.")

            edge_payloads = []
            for edge in wf_edges:
                edge_payloads.append(edge.to_dict())

            node_payloads = []
            for node in wf_nodes:
                node_payloads.append(self._create_enhanced_node_payload(session, node))

            wf_payload['nodes'] = node_payloads
            wf_payload['edges'] = edge_payloads
        else:
            # Performance optimized: only metadata
            wf_payload['nodes'] = []
            wf_payload['edges'] = []

        return wf_payload

    def workflow_list(self, session: Session, include_detail: bool = False):
        """
        List all workflows.
        """

        workflows = self.workflow_crud.get_all(session)
        if not workflows:
            return []

        wf_payloads = []
        for workflow in workflows:
            wf_payload = workflow.to_dict()
            
            if include_detail:
                # Include nodes and edges with enhanced node information
                wf_nodes = self.node_crud.filter(session, {'workflow_id': workflow.id})
                wf_payload['nodes'] = [self._create_enhanced_node_payload(session, node) for node in wf_nodes]
                wf_payload['edges'] = [edge.to_dict() for edge in self.edge_crud.filter(session, {'workflow_id': workflow.id})]
                
            wf_payloads.append(wf_payload)

        return wf_payloads

    def workflow_count(self, session: Session):
        """Count all workflows."""
        return self.workflow_crud.count(session)

    def workflow_exists(self, session: Session, workflow_id: str):
        """Check if a workflow exists by ID."""
        return self.workflow_crud.exists(session, workflow_id)

    def workflow_filter(self, session: Session, filters: dict):
        """Filter workflows based on provided criteria."""
        workflows = self.workflow_crud.filter(session, filters)
        return [workflow.id for workflow in workflows]
    
    def workflow_create(self, session: Session, name: str, description: str = None):
        """Create a new workflow (only workflow table)."""
        workflow_data = {
            'name': name,
            'description': description
        }
        workflow = self.workflow_crud.create_workflow(session, **workflow_data)
        return workflow.to_dict()
    
    def workflow_add_node(self, session: Session, workflow_id: str, **node_data):
        """Add a node to a workflow."""
        # Verify workflow exists
        if not self.workflow_crud.exists(session, workflow_id):
            raise BusinessLogicError(f"Workflow with ID {workflow_id} not found.")
        
        node_data['workflow_id'] = workflow_id
        node = self.node_crud.create_node(session, **node_data)
        return node.to_dict()
    
    def workflow_remove_node(self, session: Session, workflow_id: str, node_id: str):
        """Remove a node from a workflow."""
        # Verify workflow exists
        if not self.workflow_crud.exists(session, workflow_id):
            raise BusinessLogicError(f"Workflow with ID {workflow_id} not found.")
        
        # Verify node exists and belongs to workflow
        node = self.node_crud.find_by_id(session, node_id)
        if not node or node.workflow_id != workflow_id:
            raise BusinessLogicError(f"Node with ID {node_id} not found in workflow {workflow_id}.")
        
        deleted_node = self.node_crud.delete_node(session, node_id)
        return deleted_node.to_dict()
    
    def workflow_add_edge(self, session: Session, workflow_id: str, from_node_id: str, 
                         to_node_id: str, condition_type: str = 'success'):
        """Add an edge to a workflow."""
        # Verify workflow exists
        if not self.workflow_crud.exists(session, workflow_id):
            raise BusinessLogicError(f"Workflow with ID {workflow_id} not found.")
        
        # Verify nodes exist and belong to workflow
        from_node = self.node_crud.find_by_id(session, from_node_id)
        to_node = self.node_crud.find_by_id(session, to_node_id)
        
        if not from_node or from_node.workflow_id != workflow_id:
            raise BusinessLogicError(f"From node with ID {from_node_id} not found in workflow {workflow_id}.")
        
        if not to_node or to_node.workflow_id != workflow_id:
            raise BusinessLogicError(f"To node with ID {to_node_id} not found in workflow {workflow_id}.")
        
        edge_data = {
            'workflow_id': workflow_id,
            'from_node_id': from_node_id,
            'to_node_id': to_node_id,
            'condition_type': condition_type
        }
        edge = self.edge_crud.create_edge(session, **edge_data)
        return edge.to_dict()
    
    def workflow_remove_edge(self, session: Session, workflow_id: str, edge_id: str):
        """Remove an edge from a workflow."""
        # Verify workflow exists
        if not self.workflow_crud.exists(session, workflow_id):
            raise BusinessLogicError(f"Workflow with ID {workflow_id} not found.")
        
        # Verify edge exists and belongs to workflow
        edge = self.edge_crud.find_by_id(session, edge_id)
        if not edge or edge.workflow_id != workflow_id:
            raise BusinessLogicError(f"Edge with ID {edge_id} not found in workflow {workflow_id}.")
        
        deleted_edge = self.edge_crud.delete_edge(session, edge_id)
        return deleted_edge.to_dict()

    # ============================================================================================== NODE CRUD ==
    
    def _create_enhanced_node_payload(self, session: Session, node):
        """Create enhanced node payload with script description and output_params."""
        node_payload = node.to_dict()
        
        # Add script description and output_params if script exists
        if node.script_id:
            try:
                script = self.script_crud.find_by_id(session, node.script_id)
                if script:
                    node_payload['description'] = script.description
                    # Add script's output_params directly to node payload
                    node_payload['output_params'] = script.output_params if script.output_params else {}
                else:
                    node_payload['description'] = None
                    node_payload['output_params'] = {}
            except Exception:
                # If script not found, set default values
                node_payload['description'] = None
                node_payload['output_params'] = {}
        else:
            node_payload['description'] = None
            node_payload['output_params'] = {}
            
        return node_payload
    
    def node_get(self, session: Session, node_id: str):
        """Get a node by ID with enhanced script information."""
        node = self.node_crud.find_by_id(session, node_id)
        if not node:
            raise BusinessLogicError(f"Node with ID {node_id} not found.")
        return self._create_enhanced_node_payload(session, node)
    
    def node_exists(self, session: Session, node_id: str):
        """Check if a node exists by ID."""
        return self.node_crud.exists(session, node_id)
    
    def node_count(self, session: Session):
        """Count all nodes."""
        return self.node_crud.count(session)
    
    def node_filter(self, session: Session, filters: dict):
        """Filter nodes based on provided criteria."""
        nodes = self.node_crud.filter(session, filters)
        return [node.id for node in nodes]
    
    def node_get_by_workflow(self, session: Session, workflow_id: str):
        """Get all nodes in a workflow."""
        nodes = self.node_crud.filter(session, {'workflow_id': workflow_id})
        return [node.id for node in nodes]

    def node_get_by_workflow(self, session: Session, script_id: str):
        """Get all nodes in a workflow."""
        nodes = self.node_crud.filter(session, {'workflow_id': script_id})
        return [node.id for node in nodes]

    # ============================================================================================== EDGE CRUD ==
    
    def edge_get(self, session: Session, edge_id: str):
        """Get an edge by ID."""
        edge = self.edge_crud.find_by_id(session, edge_id)
        if not edge:
            raise BusinessLogicError(f"Edge with ID {edge_id} not found.")
        return edge.to_dict()
    
    def edge_exists(self, session: Session, edge_id: str):
        """Check if an edge exists by ID."""
        return self.edge_crud.exists(session, edge_id)
    
    def edge_count(self, session: Session):
        """Count all edges."""
        return self.edge_crud.count(session)
    
    def edge_filter(self, session: Session, filters: dict):
        """Filter edges based on provided criteria."""
        edges = self.edge_crud.filter(session, filters)
        return [edge.id for edge in edges]
    
    def edge_get_by_workflow(self, session: Session, workflow_id: str):
        """Get all edges in a workflow."""
        # Verify workflow exists
        if not self.workflow_crud.exists(session, workflow_id):
            raise BusinessLogicError(f"Workflow with ID {workflow_id} not found.")
        
        edges = self.edge_crud.filter(session, {'workflow_id': workflow_id})
        return [edge.id for edge in edges]

    # ============================================================================================== WORKFLOW BATCH OPERATIONS ==
    
    def workflow_add_nodes_batch(self, session: Session, workflow_id: str, nodes: List[dict]):
        """Add multiple nodes to a workflow at once."""
        # Verify workflow exists
        if not self.workflow_crud.exists(session, workflow_id):
            raise BusinessLogicError(f"Workflow with ID {workflow_id} not found.")
        
        added_nodes = []
        for node_data in nodes:
            node = self.workflow_add_node(session, workflow_id, **node_data)
            added_nodes.append(node)
        return added_nodes
    
    def workflow_add_edges_batch(self, session: Session, workflow_id: str, edges: List[dict]):
        """Add multiple edges to a workflow at once."""
        # Verify workflow exists
        if not self.workflow_crud.exists(session, workflow_id):
            raise BusinessLogicError(f"Workflow with ID {workflow_id} not found.")
        
        added_edges = []
        for edge_data in edges:
            edge = self.workflow_add_edge(session, workflow_id, 
                                        edge_data['from_node_id'], 
                                        edge_data['to_node_id'], 
                                        edge_data.get('condition_type', 'success'))
            added_edges.append(edge)
        return added_edges
    
    def workflow_update_structure(self, session: Session, workflow_id: str, 
                                nodes: List[dict] = None, edges: List[dict] = None):
        """Update workflow structure with new nodes and edges."""
        
        # Verify workflow exists
        if not self.workflow_crud.exists(session, workflow_id):
            raise BusinessLogicError(f"Workflow with ID {workflow_id} not found.")
        
        # Mevcut node'ları ve edge'leri al
        current_nodes = self.node_get_by_workflow(session, workflow_id)
        current_edges = self.edge_get_by_workflow(session, workflow_id)
        
        # Node'ları güncelle
        if nodes is not None:
            # Mevcut node'ları sil
            for node in current_nodes:
                self.workflow_remove_node(session, workflow_id, node['id'])
            
            # Yeni node'ları ekle
            for node_data in nodes:
                self.workflow_add_node(session, workflow_id, **node_data)
        
        # Edge'leri güncelle
        if edges is not None:
            # Mevcut edge'leri sil
            for edge in current_edges:
                self.workflow_remove_edge(session, workflow_id, edge['id'])
            
            # Yeni edge'leri ekle
            for edge_data in edges:
                self.workflow_add_edge(session, workflow_id, 
                                     edge_data['from_node_id'], 
                                     edge_data['to_node_id'], 
                                     edge_data.get('condition_type', 'success'))
        
        # Return workflow without edge validation for structure updates
        workflow = self.workflow_crud.find_by_id(session, workflow_id)
        if not workflow:
            raise BusinessLogicError(f"Workflow with ID {workflow_id} not found.")
        return workflow.to_dict()
    
    def workflow_clone(self, session: Session, workflow_id: str, new_name: str, new_description: str = None):
        """Clone a workflow with all its nodes and edges."""
        
        # Orijinal workflow'u al
        original_workflow = self.workflow_get(session, workflow_id)
        
        # Yeni workflow oluştur
        new_workflow = self.workflow_create(session, new_name, new_description or original_workflow['description'])
        
        # Node'ları kopyala
        original_node_ids = self.node_get_by_workflow(session, workflow_id)
        node_mapping = {}  # Eski ID -> Yeni ID mapping
        
        for node_id in original_node_ids:
            node = self.node_get(session, node_id)
            new_node_data = {
                'name': node['name'],
                'script_id': node['script_id'],
                'params': node['params'],
                'max_retries': node['max_retries'],
                'timeout_seconds': node['timeout_seconds']
            }
            new_node = self.workflow_add_node(session, new_workflow['id'], **new_node_data)
            node_mapping[node_id] = new_node['id']
        
        # Edge'leri kopyala
        original_edge_ids = self.edge_get_by_workflow(session, workflow_id)
        for edge_id in original_edge_ids:
            edge = self.edge_get(session, edge_id)
            new_from_node_id = node_mapping[edge['from_node_id']]
            new_to_node_id = node_mapping[edge['to_node_id']]
            
            self.workflow_add_edge(session, new_workflow['id'], 
                                  new_from_node_id, new_to_node_id, 
                                  edge['condition_type'])
        
        return new_workflow

    # ============================================================================================== SCRIPT FUNCTIONS ==
    def script_create(self, session: Session, **script_data):
        """Create a new script."""
        return self.script_crud.create_script(session=session, **script_data).to_dict()

    def script_delete(self, session: Session, script_id: str):
        """Delete a script."""
        return self.script_crud.delete_script(session, script_id).to_dict()
    
    def script_update(self, session: Session, script_id: str, **script_data):
        """Update a script."""
        return self.script_crud.update_script(session, script_id, **script_data).to_dict()
    
    def script_get(self, session: Session, script_id: str):
        """Get a script by ID."""
        return self.script_crud.find_by_id(session, script_id).to_dict()
    
    def script_list(self, session: Session):
        """List all scripts."""
        scripts = self.script_crud.get_all(session)
        return [script.to_dict() for script in scripts]

    def script_count(self, session: Session):
        """Count all scripts."""
        return self.script_crud.count(session)

    def script_exists(self, session: Session, script_id: str):
        """Check if a script exists by ID."""
        return self.script_crud.exists(session, script_id)
    
    def script_filter(self, session: Session, filters: dict):
        """Filter scripts based on provided criteria."""
        scripts = self.script_crud.filter(session, filters)
        return [script.id for script in scripts]

    # ========================================================================================= ENVIRONMENT FUNCTIONS ==
    def environment_create(self, session: Session, **environment_data):
        """Create a new environment."""
        environment = self.environment_crud.create_environment_variable(session, **environment_data)
        return environment.to_dict()

    def environment_delete(self, session: Session, environment_id: str):
        """Delete an environment."""
        environment = self.environment_crud.delete_environment_variable(session, environment_id)
        return environment.to_dict()
    
    def environment_update(self, session: Session, environment_id: str, **environment_data):
        """Update an environment."""
        environment = self.environment_crud.update_environment_variable(session, environment_id, **environment_data)
        return environment.to_dict()
    
    def environment_get(self, session: Session, environment_id: str):
        """Get an environment by ID."""
        return self.environment_crud.find_by_id(session, environment_id).to_dict()
    
    def environment_list(self, session: Session):
        """List all environments."""
        environments = self.environment_crud.get_all(session)
        return [env.to_dict() for env in environments]

    def environment_count(self, session: Session):
        """Count all environments."""
        return self.environment_crud.count(session)

    def environment_exists(self, session: Session, environment_id: str):
        """Check if an environment exists by ID."""
        return self.environment_crud.exists(session, environment_id)
    
    def environment_filter(self, session: Session, filters: dict):
        """Filter environments based on provided criteria."""
        environments = self.environment_crud.filter(session, filters)
        return [env.id for env in environments]

    def environment_delete_all(self, session: Session):
        """Delete all environments."""
        return self.environment_crud.truncate(session=session)

    # =========================================================================================== EXECUTION FUNCTIONS ==
    
    def execution_start(self, session: Session, workflow_id: str):
        """
        Start workflow execution by creating execution and execution inputs.
        """
        
        # Step 1: Validate workflow exists and has nodes
        if not self.workflow_crud.exists(session, workflow_id):
            raise BusinessLogicError(f"Workflow with ID {workflow_id} not found.")
            
        wf_nodes = self.node_crud.filter(session, {'workflow_id': workflow_id})
        if not wf_nodes:
            raise BusinessLogicError("Workflow must have at least one node to execute.")
            
        wf_edges = self.edge_crud.filter(session, {'workflow_id': workflow_id})
        
        # Step 2: Create Execution record
        execution = self.execution_crud.create_execution(session,
            workflow_id=workflow_id,
            status='pending',  # ExecutionStatus.PENDING
            pending_nodes=len(wf_nodes),
            executed_nodes=0,
            results={}
        )
        
        # Step 3: Calculate dependency count for each node
        # dependency_count = number of incoming edges to this node
        node_dependency_map = {}
        for node in wf_nodes:
            # Count incoming edges to this node
            incoming_edges_count = len([edge for edge in wf_edges if edge.to_node_id == node.id])
            node_dependency_map[node.id] = incoming_edges_count
            
        # Step 4: Create ExecutionInput records for all nodes        
        for node in wf_nodes:
            dependency_count = node_dependency_map[node.id]
            
            # Get script path for denormalization (performance optimization)
            script_path = None
            if node.script_id:
                script = self.script_crud.find_by_id(session, node.script_id)
                script_path = script.script_path if script else None
            
            execution_input_payload = {
                'execution_id': execution.id,
                'node_id': node.id,
                'priority': 0,  # Can be enhanced later with node priorities
                'dependency_count': dependency_count,
                'wait_factor': 0,  # Can be used for retry logic
                'node_name': node.name,
                'script_path': script_path,
                'node_params': node.params or {}
            }
            # Create ExecutionInput (task queue entry) with denormalized fields
            execution_input = self.execution_input_crud.create_execution_input(session, **execution_input_payload)
        
        # Step 5: Return execution details
        return {
            'execution_id': execution.id,
            'workflow_id': workflow_id,
            'status': execution.status,
            'total_nodes': len(wf_nodes),
            'pending_nodes': execution.pending_nodes,
            'executed_nodes': execution.executed_nodes,
            'started_at': execution.started_at.isoformat() if execution.started_at else None
        }

    def cancel_execution(self, session: Session, execution_id: str):
        """
        Cancel workflow execution
        """
        
        # Step 1: Validate execution exists and is cancellable
        execution = self.execution_crud.find_by_id(session, execution_id)
        if not execution:
            raise BusinessLogicError(f"Execution with ID {execution_id} not found.")
        
        if execution.status in ['completed', 'failed', 'cancelled']:
            raise BusinessLogicError(f"Cannot cancel execution with status: {execution.status}")
        
        # Step 2: Get pending execution inputs (to be canceled)
        pending_execution_inputs = self.execution_input_crud.filter(session, {'execution_id': execution_id})
        
        # Step 3: Collect deleted node information
        for exec_input in pending_execution_inputs:
            self.execution_input_crud.delete_execution_input(session, exec_input.id)
        
        results = self._combine_execution_results(session, execution_id)
        
        # Step 6: Update execution status to CANCELED
        updated_execution = self.execution_crud.update_execution(
            session, 
            execution_id,
            status='cancelled',
            ended_at=datetime.now(timezone.utc),
            results=results,
            pending_nodes=0  # No more pending nodes after cancellation
        )
        
        # Step 7: Return cancellation details
        return {
            'execution_id': execution_id,
            'workflow_id': execution.workflow_id,
            'status': updated_execution.status,
            'cancelled_at': updated_execution.ended_at.isoformat() if updated_execution.ended_at else None,
            'results': results,
        }

    def execution_get(self, session: Session, execution_id: str):
        """
        Get execution details by ID.
        """

        # Step 1: Validate execution exists
        execution = self.execution_crud.find_by_id(session, execution_id)
        if not execution:
            raise BusinessLogicError(f"Execution with ID {execution_id} not found.")

        # Step 3: Return combined results
        return execution.to_dict()

    def execution_list(self, session: Session):
        """
        List all executions.
        """

        # Step 1: Get all executions
        executions = self.execution_crud.get_all(session)
        if not executions:
            return []

        # Step 2: Return execution details
        return [execution.to_dict() for execution in executions]

    def execution_get_result(self, session: Session, execution_id: str):
        """
        Get combined results for a specific execution.
        """
        return self.execution_crud.get_result(session, execution_id)

    def execution_get_status(self, session: Session, execution_id: str):
        """
        Get the status of a specific execution.
        """
        status = self.execution_crud.get_status(session, execution_id)
        return status.value if hasattr(status, 'value') else str(status)

    def execution_count(self, session: Session):
        """
        Count all executions.
        """
        return self.execution_crud.count(session)

    def execution_exists(self, session: Session, execution_id: str):
        """
        Check if an execution exists by ID.
        """
        return self.execution_crud.exists(session, execution_id)

    def execution_filter(self, session: Session, filters: dict):
        """
        Filter executions based on provided criteria.
        """
        executions = self.execution_crud.filter(session, filters)
        return [execution.id for execution in executions]