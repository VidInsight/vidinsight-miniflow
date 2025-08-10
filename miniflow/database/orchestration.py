from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy import select, func

from .crud import *
from .models import *
from ..exceptions import ValidationError, BusinessLogicError

class DatabaseOrchestration:
    def __init__(self):
        self.workflow_crud = WorkflowCRUD()
        self.node_crud = NodeCRUD()
        self.edge_crud = EdgeCRUD()
        self.env_var_crud = EnvironmentVariableCRUD()
        self.script_crud = ScriptCRUD()
        self.execution_crud = ExecutionCRUD()
        self.execution_input_crud = ExecutionInputCRUD()
        self.execution_output_crud = ExecutionOutputCRUD()
        self.archived_execution_crud = ArchivedExecutionCRUD()
        self.audit_log_crud = AuditLogCRUD()

# ==================================================================================================== NODE FUNCTIONS ==
    def create_node(self, session: Session, node_data: dict) -> dict:
        """
        Create a new node
        """
        # 1. Validate workflow exists
        workflow = self.workflow_crud.find_by_id(session, node_data.get('workflow_id'))
        if not workflow:
            raise BusinessLogicError(f"Workflow not found: {node_data.get('workflow_id')}")

        # 2. Check if node name is unique within workflow
        existing_node = self.node_crud.get_by_name_and_workflow(
            session, node_data.get('name'), node_data.get('workflow_id')
        )
        if existing_node:
            raise ValidationError(f"Node with name '{node_data.get('name')}' already exists in workflow")

        # 3. If script_id provided, validate it exists
        if node_data.get('script_id'):
            script = self.script_crud.find_by_id(session, node_data.get('script_id'))
            if not script:
                raise BusinessLogicError(f"Script not found: {node_data.get('script_id')}")

        # 4. Create node
        node = self.node_crud.create_node(session, **node_data)

        # 5. Return API format
        return {
            'node_id': node.id,
            'name': node.name,
            'workflow_id': node.workflow_id,
        }

    def update_node(self, session: Session, node_id: str, node_data: dict) -> dict:
        """
        Update an existing node
        """
        # 1. Find existing node
        old_node = self.node_crud.find_by_id(session, node_id)
        if not old_node:
            raise BusinessLogicError(f"Node not found: {node_id}")

        # 2. If workflow_id is being changed, validate new workflow exists
        if 'workflow_id' in node_data and node_data['workflow_id'] != old_node.workflow_id:
            workflow = self.workflow_crud.find_by_id(session, node_data['workflow_id'])
            if not workflow:
                raise BusinessLogicError(f"Workflow not found: {node_data['workflow_id']}")

        # 3. If name is being changed, check uniqueness within workflow
        if 'name' in node_data and node_data['name'] != old_node.name:
            workflow_id = node_data.get('workflow_id', old_node.workflow_id)
            existing_node = self.node_crud.get_by_name_and_workflow(session, node_data['name'], workflow_id)
            if existing_node and existing_node.id != node_id:
                raise ValidationError(f"Node with name '{node_data['name']}' already exists in workflow")

        # 4. If script_id is being changed, validate it exists
        if 'script_id' in node_data and node_data['script_id']:
            script = self.script_crud.find_by_id(session, node_data['script_id'])
            if not script:
                raise BusinessLogicError(f"Script not found: {node_data['script_id']}")

        # 5. Update node
        updated_node = self.node_crud.update_node(session, node_id, **node_data)

        # 6. Return API format with updated fields
        updated_fields = list(node_data.keys())
        return {
            'node_id': updated_node.id,
            'updated_fields': updated_fields,
        }

    def delete_node(self, session: Session, node_id: str, force: bool = False) -> dict:
        """
        Delete a node
        """
        # 1. Find node to delete
        node = self.node_crud.find_by_id(session, node_id)
        if not node:
            raise BusinessLogicError(f"Node not found: {node_id}")

        # 2. Check if node has dependencies (edges) unless force=True
        if not force:
            # Check incoming edges
            incoming_edges = self.edge_crud.filter(session, {'to_node_id': node_id})
            if incoming_edges:
                raise BusinessLogicError(f"Cannot delete node '{node.name}' - it has {len(incoming_edges)} incoming dependencies. Use force=True to override.")
            
            # Check outgoing edges
            outgoing_edges = self.edge_crud.filter(session, {'from_node_id': node_id})
            if outgoing_edges:
                raise BusinessLogicError(f"Cannot delete node '{node.name}' - it has {len(outgoing_edges)} outgoing dependencies. Use force=True to override.")

        # 3. If force=True, delete related edges first
        if force:
            # Delete incoming edges
            incoming_edges = self.edge_crud.filter(session, {'to_node_id': node_id})
            for edge in incoming_edges:
                self.edge_crud.delete(session, edge.id)
            
            # Delete outgoing edges
            outgoing_edges = self.edge_crud.filter(session, {'from_node_id': node_id})
            for edge in outgoing_edges:
                self.edge_crud.delete(session, edge.id)

        # 4. Delete the node
        deleted_node = self.node_crud.delete_node(session, node_id)

        # 5. Return API format
        return {
            'node_id': deleted_node.id,
            'node_name': deleted_node.name,
            'workflow_id': deleted_node.workflow_id
        }

    def validate_node(self, session: Session, node_id: str) -> dict:
        """
        Validate a node configuration
        """
        # 1. Find node
        node = self.node_crud.find_by_id(session, node_id)
        if not node:
            raise BusinessLogicError(f"Node not found: {node_id}")

        validation_errors = []
        validation_warnings = []

        # 2. Validate workflow exists
        workflow = self.workflow_crud.find_by_id(session, node.workflow_id)
        if not workflow:
            validation_errors.append(f"Associated workflow not found: {node.workflow_id}")

        # 3. Validate script exists if script_id is set
        if node.script_id:
            script = self.script_crud.find_by_id(session, node.script_id)
            if not script:
                validation_errors.append(f"Associated script not found: {node.script_id}")
        else:
            validation_warnings.append("No script associated with this node")

        # 4. Validate timeout and retries
        if node.timeout_seconds <= 0:
            validation_errors.append("Timeout must be greater than 0")

        if node.max_retries < 0:
            validation_errors.append("Max retries cannot be negative")

        # 5. Check for circular dependencies (basic check)
        # This would require a more complex graph traversal for complete validation
        if self._has_self_dependency(session, node_id):
            validation_errors.append("Node has circular dependency to itself")

        # 6. Return validation result
        is_valid = len(validation_errors) == 0
        return {
            'node_id': node_id,
            'is_valid': is_valid,
            'validation_errors': validation_errors,
            'validation_warnings': validation_warnings
        }

    def search_nodes(self, session: Session, search_criteria: dict) -> dict:
        """
        Search/filter nodes based on criteria
        """
        nodes = self.node_crud.search_nodes(session, **search_criteria)
        
        node_list = []
        for node in nodes:
            node_dict = node.to_dict()
            node_dict['node_id'] = node_dict['id']  # Add consistent field name
            
            # Add script name if available
            if node.script_id:
                try:
                    script = self.script_crud.find_by_id(session, node.script_id)
                    node_dict['script_name'] = script.name if script else None
                except:
                    node_dict['script_name'] = None
            
            node_list.append(node_dict)
        
        return {
            'message': 'Node search completed',
            'data': node_list,
            'total_count': len(node_list)
        }

    def get_nodes(self, session: Session, workflow_id: Optional[str] = None, 
                 page: Optional[int] = None, page_size: Optional[int] = None) -> dict:
        """
        List all nodes or nodes for a specific workflow
        """
        if workflow_id:
            nodes = self.node_crud.get_nodes_by_workflow(session, workflow_id)
        else:
            skip = (page - 1) * page_size if page and page_size else 0
            limit = page_size if page_size else 100
            nodes = self.node_crud.get_all(session, skip=skip, limit=limit)
        
        node_list = []
        for node in nodes:
            node_dict = node.to_dict()
            node_dict['node_id'] = node_dict['id']  # Add consistent field name
            
            # Add script name if available
            if node.script_id:
                try:
                    script = self.script_crud.find_by_id(session, node.script_id)
                    node_dict['script_name'] = script.name if script else None
                except:
                    node_dict['script_name'] = None
            
            node_list.append(node_dict)

        return {
            'message': 'Nodes listed successfully',
            'data': node_list,
            'total_count': len(node_list)
        }

    def get_node(self, session: Session, node_id: str) -> dict:
        """
        Get detailed information about a specific node
        """
        # 1. Find node
        node = self.node_crud.find_by_id(session, node_id)
        if not node:
            raise BusinessLogicError(f"Node not found: {node_id}")

        # 2. Prepare node data
        node_dict = node.to_dict()
        node_dict['node_id'] = node_dict['id']  # Add consistent field name

        # 3. Add script information if available
        if node.script_id:
            script = self.script_crud.find_by_id(session, node.script_id)
            node_dict['script_name'] = script.name if script else None

        # 4. Add workflow information
        workflow = self.workflow_crud.find_by_id(session, node.workflow_id)
        node_dict['workflow_name'] = workflow.name if workflow else None

        # 5. Add dependency information
        incoming_edges = self.edge_crud.filter(session, {'to_node_id': node_id})
        outgoing_edges = self.edge_crud.filter(session, {'from_node_id': node_id})
        
        node_dict['dependency_count'] = len(incoming_edges)
        node_dict['dependent_count'] = len(outgoing_edges)

        return {
            'message': 'Node retrieved successfully',
            'data': node_dict
        }

    def count_nodes(self, session: Session, workflow_id: Optional[str] = None) -> dict:
        """
        Count nodes total or by workflow
        """
        if workflow_id:
            count = self.node_crud.count_by_workflow(session, workflow_id)
        else:
            count = self.node_crud.count(session)

        return {
            'message': 'Node count retrieved successfully',
            'node_count': count
        }

    def node_exists(self, session: Session, node_id: str) -> dict:
        """
        Check if a node exists
        """
        exists = self.node_crud.exists(session, node_id)
        node_name = None
        if exists:
            try:
                node = self.node_crud.find_by_id(session, node_id)
                node_name = node.name if node else None
            except:
                pass
        
        return {
            'message': 'Node existence checked',
            'is_exists': exists,
            'name': node_name
        }

    def _has_self_dependency(self, session: Session, node_id: str) -> bool:
        """
        Check if node has a direct self-dependency (edge from itself to itself)
        """
        try:
            edges = self.edge_crud.filter(session, {'from_node_id': node_id, 'to_node_id': node_id})
            return len(edges) > 0
        except Exception:
            return False

# ==================================================================================================== EDGE FUNCTIONS ==
    def create_edge(self, session: Session, edge_data: dict) -> dict:
        """
        Create a new edge
        """
        # 1. Validate from_node exists
        from_node = self.node_crud.find_by_id(session, edge_data.get('from_node_id'))
        if not from_node:
            raise BusinessLogicError(f"From node not found: {edge_data.get('from_node_id')}")

        # 2. Validate to_node exists
        to_node = self.node_crud.find_by_id(session, edge_data.get('to_node_id'))
        if not to_node:
            raise BusinessLogicError(f"To node not found: {edge_data.get('to_node_id')}")

        # 3. Check if nodes are in the same workflow
        if from_node.workflow_id != to_node.workflow_id:
            raise ValidationError("Nodes must be in the same workflow")

        # 4. Set workflow_id automatically
        edge_data['workflow_id'] = from_node.workflow_id

        # 5. Check if edge already exists between these nodes
        if self.edge_crud.check_edge_exists(session, edge_data.get('from_node_id'), edge_data.get('to_node_id')):
            raise ValidationError(f"Edge already exists between nodes {from_node.name} and {to_node.name}")

        # 6. Check for circular dependency (prevent self-loops)
        if edge_data.get('from_node_id') == edge_data.get('to_node_id'):
            raise ValidationError("Self-loops are not allowed")

        # 7. Create edge
        edge = self.edge_crud.create_edge(session, **edge_data)

        # 8. Return API format
        return {
            'edge_id': edge.id,
            'workflow_id': edge.workflow_id,
            'from_node_id': edge.from_node_id,
            'to_node_id': edge.to_node_id,
            'created_at': edge.created_at.isoformat() if edge.created_at else None
        }

    def update_edge(self, session: Session, edge_id: str, edge_data: dict) -> dict:
        """
        Update an existing edge
        """
        # 1. Find existing edge
        old_edge = self.edge_crud.find_by_id(session, edge_id)
        if not old_edge:
            raise BusinessLogicError(f"Edge not found: {edge_id}")

        # 2. If nodes are being changed, validate them
        if 'from_node_id' in edge_data or 'to_node_id' in edge_data:
            from_node_id = edge_data.get('from_node_id', old_edge.from_node_id)
            to_node_id = edge_data.get('to_node_id', old_edge.to_node_id)

            # Validate nodes exist
            from_node = self.node_crud.find_by_id(session, from_node_id)
            to_node = self.node_crud.find_by_id(session, to_node_id)
            
            if not from_node:
                raise BusinessLogicError(f"From node not found: {from_node_id}")
            if not to_node:
                raise BusinessLogicError(f"To node not found: {to_node_id}")

            # Check same workflow
            if from_node.workflow_id != to_node.workflow_id:
                raise ValidationError("Nodes must be in the same workflow")

            # Check for circular dependency
            if from_node_id == to_node_id:
                raise ValidationError("Self-loops are not allowed")

            # Check if edge already exists (unless updating to the same edge)
            if (from_node_id != old_edge.from_node_id or to_node_id != old_edge.to_node_id):
                if self.edge_crud.check_edge_exists(session, from_node_id, to_node_id):
                    raise ValidationError(f"Edge already exists between nodes {from_node.name} and {to_node.name}")

        # 3. Update edge
        updated_edge = self.edge_crud.update_edge(session, edge_id, **edge_data)

        # 4. Return API format with updated fields
        updated_fields = list(edge_data.keys())
        return {
            'edge_id': updated_edge.id,
            'updated_fields': updated_fields,
            'updated_at': updated_edge.updated_at.isoformat() if updated_edge.updated_at else None
        }

    def delete_edge(self, session: Session, edge_id: str) -> dict:
        """
        Delete an edge
        """
        # 1. Find edge to delete
        edge = self.edge_crud.find_by_id(session, edge_id)
        if not edge:
            raise BusinessLogicError(f"Edge not found: {edge_id}")

        # 2. Get node names for response
        from_node = self.node_crud.find_by_id(session, edge.from_node_id)
        to_node = self.node_crud.find_by_id(session, edge.to_node_id)
        
        from_node_name = from_node.name if from_node else None
        to_node_name = to_node.name if to_node else None

        # 3. Delete the edge
        deleted_edge = self.edge_crud.delete_edge(session, edge_id)

        # 4. Return API format
        return {
            'edge_id': deleted_edge.id,
            'from_node_name': from_node_name,
            'to_node_name': to_node_name,
            'workflow_id': deleted_edge.workflow_id
        }

    def validate_edge(self, session: Session, edge_id: str) -> dict:
        """
        Validate an edge configuration
        """
        # 1. Find edge
        edge = self.edge_crud.find_by_id(session, edge_id)
        if not edge:
            raise BusinessLogicError(f"Edge not found: {edge_id}")

        validation_errors = []
        validation_warnings = []

        # 2. Validate from_node exists
        try:
            from_node = self.node_crud.find_by_id(session, edge.from_node_id)
        except:
            from_node = None
            validation_errors.append(f"From node not found: {edge.from_node_id}")

        # 3. Validate to_node exists
        try:
            to_node = self.node_crud.find_by_id(session, edge.to_node_id)
        except:
            to_node = None
            validation_errors.append(f"To node not found: {edge.to_node_id}")

        # 4. If both nodes exist, validate workflow consistency
        if from_node and to_node:
            if from_node.workflow_id != to_node.workflow_id:
                validation_errors.append("Nodes are not in the same workflow")
            
            # Check for self-loop
            if edge.from_node_id == edge.to_node_id:
                validation_errors.append("Self-loops are not allowed")

        # 5. Check for circular dependencies (basic check)
        if from_node and to_node and not validation_errors:
            if self._has_circular_dependency(session, edge.from_node_id, edge.to_node_id):
                validation_warnings.append("Edge may create circular dependency in workflow")

        # 6. Return validation result
        is_valid = len(validation_errors) == 0
        return {
            'edge_id': edge_id,
            'is_valid': is_valid,
            'validation_errors': validation_errors,
            'validation_warnings': validation_warnings
        }

    def search_edges(self, session: Session, search_criteria: dict) -> dict:
        """
        Search/filter edges based on criteria
        """
        edges = self.edge_crud.search_edges(session, **search_criteria)
        
        edge_list = []
        for edge in edges:
            edge_dict = edge.to_dict()
            edge_dict['edge_id'] = edge_dict['id']  # Add consistent field name
            
            # Add node names if available
            try:
                from_node = self.node_crud.find_by_id(session, edge.from_node_id)
                edge_dict['from_node_name'] = from_node.name if from_node else None
            except:
                edge_dict['from_node_name'] = None
                
            try:
                to_node = self.node_crud.find_by_id(session, edge.to_node_id)
                edge_dict['to_node_name'] = to_node.name if to_node else None
            except:
                edge_dict['to_node_name'] = None
            
            edge_list.append(edge_dict)

        return {
            'message': 'Edge search completed',
            'data': edge_list,
            'total_count': len(edge_list)
        }

    def get_edges(self, session: Session, workflow_id: Optional[str] = None, 
                 page: Optional[int] = None, page_size: Optional[int] = None) -> dict:
        """
        List all edges or edges for a specific workflow
        """
        if workflow_id:
            edges = self.edge_crud.get_edges_by_workflow(session, workflow_id)
        else:
            skip = (page - 1) * page_size if page and page_size else 0
            limit = page_size if page_size else 100
            edges = self.edge_crud.get_all(session, skip=skip, limit=limit)
        
        edge_list = []
        for edge in edges:
            edge_dict = edge.to_dict()
            edge_dict['edge_id'] = edge_dict['id']  # Add consistent field name
            
            # Add node names if available
            try:
                from_node = self.node_crud.find_by_id(session, edge.from_node_id)
                edge_dict['from_node_name'] = from_node.name if from_node else None
            except:
                edge_dict['from_node_name'] = None
                
            try:
                to_node = self.node_crud.find_by_id(session, edge.to_node_id)
                edge_dict['to_node_name'] = to_node.name if to_node else None
            except:
                edge_dict['to_node_name'] = None
            
            edge_list.append(edge_dict)

        return {
            'message': 'Edges listed successfully',
            'data': edge_list,
            'total_count': len(edge_list)
        }

    def get_edge(self, session: Session, edge_id: str) -> dict:
        """
        Get detailed information about a specific edge
        """
        # 1. Find edge
        edge = self.edge_crud.find_by_id(session, edge_id)
        if not edge:
            raise BusinessLogicError(f"Edge not found: {edge_id}")

        # 2. Prepare edge data
        edge_dict = edge.to_dict()
        edge_dict['edge_id'] = edge_dict['id']  # Add consistent field name

        # 3. Add node information
        try:
            from_node = self.node_crud.find_by_id(session, edge.from_node_id)
            edge_dict['from_node_name'] = from_node.name if from_node else None
        except:
            edge_dict['from_node_name'] = None
            
        try:
            to_node = self.node_crud.find_by_id(session, edge.to_node_id)
            edge_dict['to_node_name'] = to_node.name if to_node else None
        except:
            edge_dict['to_node_name'] = None

        # 4. Add workflow information
        try:
            workflow = self.workflow_crud.find_by_id(session, edge.workflow_id)
            edge_dict['workflow_name'] = workflow.name if workflow else None
        except:
            edge_dict['workflow_name'] = None

        return {
            'message': 'Edge retrieved successfully',
            'data': edge_dict
        }

    def count_edges(self, session: Session, workflow_id: Optional[str] = None) -> dict:
        """
        Count edges total or by workflow
        """
        if workflow_id:
            count = self.edge_crud.count_by_workflow(session, workflow_id)
        else:
            count = self.edge_crud.count(session)

        return {
            'message': 'Edge count retrieved successfully',
            'node_count': count  # Using node_count to match schema
        }

    def edge_exists(self, session: Session, edge_id: str) -> dict:
        """
        Check if an edge exists
        """
        exists = self.edge_crud.exists(session, edge_id)
        
        return {
            'message': 'Edge existence checked',
            'is_exists': exists
        }

    def _has_circular_dependency(self, session: Session, from_node_id: str, to_node_id: str) -> bool:
        """
        Check if creating an edge would create a circular dependency
        This is a simplified check - for complete validation, a full graph traversal would be needed
        """
        try:
            # Check if to_node has a path back to from_node
            visited = set()
            return self._check_path_exists(session, to_node_id, from_node_id, visited)
        except Exception:
            return False

    def _check_path_exists(self, session: Session, start_node: str, target_node: str, visited: set) -> bool:
        """
        Recursively check if a path exists from start_node to target_node
        """
        if start_node in visited:
            return False
        
        if start_node == target_node:
            return True
            
        visited.add(start_node)
        
        # Get all outgoing edges from start_node
        outgoing_edges = self.edge_crud.filter(session, {'from_node_id': start_node})
        
        for edge in outgoing_edges:
            if self._check_path_exists(session, edge.to_node_id, target_node, visited):
                return True
                
        visited.remove(start_node)
        return False

# ==================================================================================== ENVIRONMENT VARIABLE FUNCTIONS ==
    def create_env_var(self, session: Session, env_var_data: dict) -> dict:
        """
        Create a new environment variable
        """
        # 1. Check if environment variable name already exists
        existing_env_var = self.env_var_crud.get_by_name(session, env_var_data.get('name'))
        if existing_env_var:
            raise ValidationError(f"Environment variable with name '{env_var_data.get('name')}' already exists")

        # 2. Validate environment variable name (no special chars, etc.)
        name = env_var_data.get('name', '')
        if not name or not name.replace('_', '').replace('-', '').isalnum():
            raise ValidationError("Environment variable name must contain only alphanumeric characters, hyphens, and underscores")

        # 3. Handle encryption if needed - disabled for simplified implementation
        # if env_var_data.get('is_encrypted', False):
        #     env_var_data['value'] = self._encrypt_value(env_var_data.get('value', ''))

        # 4. Create environment variable
        env_var = self.env_var_crud.create_env_var(session, **env_var_data)

        # 5. Return API format
        return {
            'env_var_id': env_var.id,
            'name': env_var.name,
            'created_at': env_var.created_at.isoformat() if env_var.created_at else None,
            'message': 'Environment variable created successfully'
        }

    def update_env_var(self, session: Session, env_var_id: str, env_var_data: dict) -> dict:
        """
        Update an existing environment variable
        """
        # 1. Find existing environment variable
        old_env_var = self.env_var_crud.find_by_id(session, env_var_id)
        if not old_env_var:
            raise BusinessLogicError(f"Environment variable not found: {env_var_id}")

        # 2. If name is being changed, check uniqueness
        if 'name' in env_var_data and env_var_data['name'] != old_env_var.name:
            existing_env_var = self.env_var_crud.get_by_name(session, env_var_data['name'])
            if existing_env_var and existing_env_var.id != env_var_id:
                raise ValidationError(f"Environment variable with name '{env_var_data['name']}' already exists")
            
            # Validate new name
            name = env_var_data['name']
            if not name or not name.replace('_', '').replace('-', '').isalnum():
                raise ValidationError("Environment variable name must contain only alphanumeric characters, hyphens, and underscores")

        # 3. Handle encryption changes - disabled for simplified implementation
        # if 'value' in env_var_data:
        #     is_encrypted = env_var_data.get('is_encrypted', False)
        #     if is_encrypted:
        #         env_var_data['value'] = self._encrypt_value(env_var_data['value'])

        # 4. Update environment variable
        updated_env_var = self.env_var_crud.update_env_var(session, env_var_id, **env_var_data)

        # 5. Return API format with updated fields
        updated_fields = list(env_var_data.keys())
        return {
            'env_var_id': updated_env_var.id,
            'updated_fields': updated_fields,
            'updated_at': updated_env_var.updated_at.isoformat() if updated_env_var.updated_at else None
        }

    def delete_env_var(self, session: Session, env_var_id: str) -> dict:
        """
        Delete an environment variable
        """
        # 1. Find environment variable to delete
        env_var = self.env_var_crud.find_by_id(session, env_var_id)
        if not env_var:
            raise BusinessLogicError(f"Environment variable not found: {env_var_id}")

        # 2. Check if environment variable is being used by any nodes
        # Note: This would require checking node params for references to this env var
        # For now, we'll allow deletion but could add usage checking later

        # 3. Delete the environment variable
        deleted_env_var = self.env_var_crud.delete_env_var(session, env_var_id)

        # 4. Return API format
        return {
            'env_var_id': deleted_env_var.id,
            'env_var_name': deleted_env_var.name
        }

    def validate_env_var(self, session: Session, env_var_id: str) -> dict:
        """
        Validate an environment variable configuration
        """
        # 1. Find environment variable
        env_var = self.env_var_crud.find_by_id(session, env_var_id)
        if not env_var:
            raise BusinessLogicError(f"Environment variable not found: {env_var_id}")

        validation_errors = []
        validation_warnings = []

        # 2. Validate name format
        name = env_var.name
        if not name or not name.replace('_', '').replace('-', '').isalnum():
            validation_errors.append("Environment variable name must contain only alphanumeric characters, hyphens, and underscores")

        # 3. Check for empty value
        if not env_var.value:
            validation_warnings.append("Environment variable has empty value")

        # 4. Check encryption consistency - disabled for simplified implementation
        # if env_var.is_encrypted:
        #     if len(env_var.value) < 10:
        #         validation_warnings.append("Encrypted value seems too short - encryption might have failed")

        # 5. Check for potential security issues
        # Simple security check for sensitive variable names
        if any(keyword in env_var.name.lower() for keyword in ['password', 'secret', 'key', 'token']):
            validation_warnings.append("Variable name suggests sensitive data - consider secure handling")

        # 6. Return validation result
        is_valid = len(validation_errors) == 0
        return {
            'env_var_id': env_var_id,
            'is_valid': is_valid,
            'validation_errors': validation_errors,
            'validation_warnings': validation_warnings
        }

    def search_env_vars(self, session: Session, search_criteria: dict) -> dict:
        """
        Search/filter environment variables based on criteria
        """
        env_vars = self.env_var_crud.search_env_vars(session, **search_criteria)
        
        env_var_list = []
        for env_var in env_vars:
            env_var_dict = env_var.to_dict()
            env_var_dict['env_var_id'] = env_var_dict['id']  # Add consistent field name
            
            # Mask sensitive values for security
            if any(keyword in env_var.name.lower() for keyword in ['password', 'secret', 'key', 'token']):
                env_var_dict['value'] = '***MASKED***'
            
            env_var_list.append(env_var_dict)

        return {
            'message': 'Environment variable search completed',
            'data': env_var_list,
            'total_count': len(env_var_list)
        }

    def get_env_vars(self, session: Session, include_encrypted: bool = True, 
                    page: Optional[int] = None, page_size: Optional[int] = None) -> dict:
        """
        List environment variables with optional filtering
        """
        if include_encrypted:
            skip = (page - 1) * page_size if page and page_size else 0
            limit = page_size if page_size else 100
            env_vars = self.env_var_crud.get_all(session, skip=skip, limit=limit)
        else:
            env_vars = self.env_var_crud.get_unencrypted_vars(session)
        
        env_var_list = []
        for env_var in env_vars:
            env_var_dict = env_var.to_dict()
            env_var_dict['env_var_id'] = env_var_dict['id']  # Add consistent field name
            
            # Mask sensitive values for security
            if any(keyword in env_var.name.lower() for keyword in ['password', 'secret', 'key', 'token']):
                env_var_dict['value'] = '***MASKED***'
            
            env_var_list.append(env_var_dict)

        return {
            'message': 'Environment variables listed successfully',
            'data': env_var_list,
            'total_count': len(env_var_list)
        }

    def get_env_var(self, session: Session, env_var_id: str, include_value: bool = False) -> dict:
        """
        Get detailed information about a specific environment variable
        """
        # 1. Find environment variable
        env_var = self.env_var_crud.find_by_id(session, env_var_id)
        if not env_var:
            raise BusinessLogicError(f"Environment variable not found: {env_var_id}")

        # 2. Prepare environment variable data
        env_var_dict = env_var.to_dict()
        env_var_dict['env_var_id'] = env_var_dict['id']  # Add consistent field name

        # 3. Handle sensitive value masking
        if not include_value:
            env_var_dict['value'] = '***HIDDEN***'
        elif any(keyword in env_var.name.lower() for keyword in ['password', 'secret', 'key', 'token']):
            env_var_dict['value'] = '***MASKED***'

        return {
            'message': 'Environment variable retrieved successfully',
            'data': env_var_dict
        }

    def count_env_vars(self, session: Session, include_encrypted: Optional[bool] = None) -> dict:
        """
        Count environment variables with optional encryption filtering
        """
        if include_encrypted is None:
            count = self.env_var_crud.count(session)
        elif include_encrypted:
            encrypted_vars = self.env_var_crud.get_encrypted_vars(session)
            count = len(encrypted_vars)
        else:
            unencrypted_vars = self.env_var_crud.get_unencrypted_vars(session)
            count = len(unencrypted_vars)

        return {
            'message': 'Environment variable count retrieved successfully',
            'env_var_count': count
        }

    def env_var_exists(self, session: Session, env_var_id: str) -> dict:
        """
        Check if an environment variable exists
        """
        exists = self.env_var_crud.exists(session, env_var_id)
        
        return {
            'message': 'Environment variable existence checked',
            'is_exists': exists
        }

    def delete_all_env_vars(self, session: Session) -> dict:
        """
        Delete all environment variables (dangerous operation)
        """
        deleted_count = self.env_var_crud.bulk_delete_all(session)
        
        return {
            'message': 'All environment variables deleted successfully',
            'deleted_count': deleted_count
        }

    def _encrypt_value(self, value: str) -> str:
        """
        Encrypt environment variable value
        Note: This is a placeholder implementation.
        In production, use proper encryption like AES with a secure key management system.
        """
        # This is a simple base64 encoding for demonstration
        # In real implementation, use proper encryption
        import base64
        return base64.b64encode(value.encode()).decode()

    def _decrypt_value(self, encrypted_value: str) -> str:
        """
        Decrypt environment variable value
        Note: This is a placeholder implementation.
        """
        import base64
        try:
            return base64.b64decode(encrypted_value.encode()).decode()
        except:
            return encrypted_value  # Return as-is if decryption fails

# ================================================================================================== SCRIPT FUNCTIONS ==
    def create_script(self, session: Session, script_data: dict) -> dict:
        """
        Create a new script with file system management
        """
        import os
        from datetime import datetime
        
        # 1. Check if script name already exists
        existing_script = self.script_crud.get_by_name(session, script_data.get('name'))
        if existing_script:
            raise ValidationError(f"Script with name '{script_data.get('name')}' already exists")

        # 2. Validate script name (no special chars for file safety)
        name = script_data.get('name', '')
        if not name or not name.replace('_', '').replace('-', '').isalnum():
            raise ValidationError("Script name must contain only alphanumeric characters, hyphens, and underscores")

        # 3. Determine language from content or explicit setting
        script_content = script_data.get('script_content', '')
        language = script_data.get('language', self._detect_script_language(script_content))
        
        # 4. Create script file path
        script_dir = "scripts"  # Base directory for scripts
        os.makedirs(script_dir, exist_ok=True)
        
        file_extension = self._get_file_extension(language)
        script_path = os.path.join(script_dir, f"{name}{file_extension}")
        
        # 5. Write script content to file
        try:
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(script_content)
        except Exception as e:
            raise BusinessLogicError(f"Failed to write script file: {str(e)}")

        # 6. Prepare script data for database
        db_script_data = {
            'name': name,
            'description': script_data.get('description'),
            'language': language,
            'script_path': os.path.abspath(script_path),
            'input_params': script_data.get('input_params', {}),
            'output_params': script_data.get('output_params', {}),
            'test_status': 'untested'  # Default status
        }

        # 7. Create script in database
        script = self.script_crud.create_script(session, **db_script_data)

        # 8. Return API format
        return {
            'script_id': script.id,
            'name': script.name,
            'language': script.language,
            'script_path': script.script_path,
            'created_at': script.created_at.isoformat() if script.created_at else None
        }

    def update_script(self, session: Session, script_id: str, script_data: dict) -> dict:
        """
        Update an existing script with file system management
        """
        import os
        
        # 1. Find existing script
        old_script = self.script_crud.find_by_id(session, script_id)
        if not old_script:
            raise BusinessLogicError(f"Script not found: {script_id}")

        # 2. If name is being changed, check uniqueness
        if 'name' in script_data and script_data['name'] != old_script.name:
            existing_script = self.script_crud.get_by_name(session, script_data['name'])
            if existing_script and existing_script.id != script_id:
                raise ValidationError(f"Script with name '{script_data['name']}' already exists")
            
            # Validate new name
            name = script_data['name']
            if not name or not name.replace('_', '').replace('-', '').isalnum():
                raise ValidationError("Script name must contain only alphanumeric characters, hyphens, and underscores")

        # 3. Handle script content update
        if 'script_content' in script_data:
            script_content = script_data['script_content']
            
            # Update language if changed or detect from content
            if 'language' in script_data:
                language = script_data['language']
            else:
                language = self._detect_script_language(script_content)
                script_data['language'] = language
            
            # Handle file path update if name or language changed
            if 'name' in script_data or language != old_script.language:
                script_dir = os.path.dirname(old_script.script_path)
                file_extension = self._get_file_extension(language)
                new_name = script_data.get('name', old_script.name)
                new_script_path = os.path.join(script_dir, f"{new_name}{file_extension}")
                
                # Write to new file
                try:
                    with open(new_script_path, 'w', encoding='utf-8') as f:
                        f.write(script_content)
                    
                    # Remove old file if path changed
                    if new_script_path != old_script.script_path and os.path.exists(old_script.script_path):
                        os.remove(old_script.script_path)
                    
                    script_data['script_path'] = os.path.abspath(new_script_path)
                    
                except Exception as e:
                    raise BusinessLogicError(f"Failed to update script file: {str(e)}")
            else:
                # Just update existing file
                try:
                    with open(old_script.script_path, 'w', encoding='utf-8') as f:
                        f.write(script_content)
                except Exception as e:
                    raise BusinessLogicError(f"Failed to update script file: {str(e)}")

        # 4. Update script in database
        updated_script = self.script_crud.update_script(session, script_id, **script_data)

        # 5. Return API format with updated fields
        updated_fields = list(script_data.keys())
        return {
            'script_id': updated_script.id,
            'updated_fields': updated_fields,
            'updated_at': updated_script.updated_at.isoformat() if updated_script.updated_at else None
        }

    def delete_script(self, session: Session, script_id: str, force: bool = False) -> dict:
        """
        Delete a script with usage checking and file system cleanup
        """
        import os
        
        # 1. Find script to delete
        script = self.script_crud.find_by_id(session, script_id)
        if not script:
            raise BusinessLogicError(f"Script not found: {script_id}")

        # 2. Check if script is being used by any nodes (unless force delete)
        if not force:
            # This is a placeholder - in real implementation, check node references
            nodes_using_script = []  # self.node_crud.get_by_script_id(session, script_id)
            if nodes_using_script:
                raise BusinessLogicError(f"Cannot delete script - it is being used by {len(nodes_using_script)} node(s). Use force=True to override.")

        # 3. Delete the script file
        if script.script_path and os.path.exists(script.script_path):
            try:
                os.remove(script.script_path)
            except Exception as e:
                # Log warning but don't fail the database deletion
                print(f"Warning: Failed to delete script file {script.script_path}: {str(e)}")

        # 4. Delete from database
        deleted_script = self.script_crud.delete_script(session, script_id)

        # 5. Return API format
        return {
            'script_id': deleted_script.id,
            'script_name': deleted_script.name,
            'affected_nodes': 0  # Placeholder - would be calculated from usage check
        }

    def validate_script(self, session: Session, script_id: str) -> dict:
        """
        Validate a script's configuration and content
        """
        import os
        
        # 1. Find script
        script = self.script_crud.find_by_id(session, script_id)
        if not script:
            raise BusinessLogicError(f"Script not found: {script_id}")

        validation_errors = []
        validation_warnings = []

        # 2. Validate name format
        name = script.name
        if not name or not name.replace('_', '').replace('-', '').isalnum():
            validation_errors.append("Script name must contain only alphanumeric characters, hyphens, and underscores")

        # 3. Check file existence
        if not script.script_path or not os.path.exists(script.script_path):
            validation_errors.append("Script file not found on filesystem")
        else:
            # 4. Validate file content
            try:
                with open(script.script_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                if not content.strip():
                    validation_warnings.append("Script file is empty")
                
                # 5. Basic syntax validation for Python scripts
                if script.language.lower() == 'python':
                    try:
                        compile(content, script.script_path, 'exec')
                    except SyntaxError as e:
                        validation_errors.append(f"Python syntax error: {str(e)}")
                        
            except Exception as e:
                validation_errors.append(f"Failed to read script file: {str(e)}")

        # 6. Check parameter definitions
        if not script.input_params:
            validation_warnings.append("No input parameters defined")
        
        if not script.output_params:
            validation_warnings.append("No output parameters defined")

        # 7. Return validation result
        is_valid = len(validation_errors) == 0
        return {
            'script_id': script_id,
            'is_valid': is_valid,
            'validation_errors': validation_errors,
            'validation_warnings': validation_warnings
        }

    def search_scripts(self, session: Session, search_criteria: dict) -> dict:
        """
        Search/filter scripts based on criteria
        """
        scripts = self.script_crud.search_scripts(session, **search_criteria)
        
        script_list = []
        for script in scripts:
            script_dict = script.to_dict()
            script_dict['script_id'] = script_dict['id']  # Add consistent field name
            script_list.append(script_dict)

        return {
            'message': 'Script search completed',
            'data': script_list,
            'total_count': len(script_list)
        }

    def get_scripts(self, session: Session, language: Optional[str] = None,
test_status: Optional[str] = None, page: Optional[int] = None,
                   page_size: Optional[int] = None) -> dict:
        """
        List scripts with optional filtering
        """
        if language and test_status:
            scripts = self.script_crud.filter(session, {'language': language, 'test_status': test_status})
        elif language:
            scripts = self.script_crud.get_by_language(session, language)
        elif test_status:
            scripts = self.script_crud.get_by_test_status(session, test_status)
        else:
            skip = (page - 1) * page_size if page and page_size else 0
            limit = page_size if page_size else 100
            scripts = self.script_crud.get_all(session, skip=skip, limit=limit)
        
        script_list = []
        for script in scripts:
            script_dict = script.to_dict()
            script_dict['script_id'] = script_dict['id']  # Add consistent field name
            script_list.append(script_dict)

        return {
            'message': 'Scripts listed successfully',
            'data': script_list,
            'total_count': len(script_list)
        }

    def get_script(self, session: Session, script_id: str, include_content: bool = False) -> dict:
        """
        Get detailed information about a specific script
        """
        # 1. Find script
        script = self.script_crud.find_by_id(session, script_id)
        if not script:
            raise BusinessLogicError(f"Script not found: {script_id}")
        
        # 2. Prepare script data
        script_dict = script.to_dict()
        script_dict['script_id'] = script_dict['id']  # Add consistent field name
        
        # 3. Include file content if requested
        if include_content and script.script_path:
            import os
            if os.path.exists(script.script_path):
                try:
                    with open(script.script_path, 'r', encoding='utf-8') as f:
                        script_dict['script_content'] = f.read()
                except Exception as e:
                    script_dict['script_content'] = f"Error reading file: {str(e)}"
            else:
                script_dict['script_content'] = "File not found"

        return {
            'message': 'Script retrieved successfully',
            'data': script_dict
        }

    def count_scripts(self, session: Session, group_by: Optional[str] = None) -> dict:
        """
        Count scripts with optional grouping
        """
        total_count = self.script_crud.count(session)
        
        result = {
            'message': 'Script count retrieved successfully',
            'script_count': total_count
        }
        
        if group_by == 'language':
            language_counts = self.script_crud.count_by_language(session)
            result['by_language'] = language_counts
        elif group_by == 'test_status':
            status_counts = self.script_crud.count_by_test_status(session)
            result['by_test_status'] = status_counts
        elif group_by == 'both':
            result['by_language'] = self.script_crud.count_by_language(session)
            result['by_test_status'] = self.script_crud.count_by_test_status(session)

        return result

    def script_exists(self, session: Session, script_id: str) -> dict:
        """
        Check if a script exists
        """
        exists = self.script_crud.exists(session, script_id)
        
        return {
            'message': 'Script existence checked',
            'is_exists': exists
        }

    def test_script(self, session: Session, script_id: str, test_data: dict) -> dict:
        """
        Test a script execution (placeholder implementation)
        """
        import time
        import subprocess
        import json
        import tempfile
        import os
        
        # 1. Find script
        script = self.script_crud.find_by_id(session, script_id)
        if not script:
            raise BusinessLogicError(f"Script not found: {script_id}")

        # 2. Validate script file exists
        if not script.script_path or not os.path.exists(script.script_path):
            return {
                'script_id': script_id,
                'test_status': 'failed',
                'execution_time': 0.0,
                'test_output': None,
                'test_errors': ['Script file not found']
            }

        # 3. Prepare test execution
        test_input = test_data.get('test_input', {})
        timeout_seconds = test_data.get('timeout_seconds', 30)
        
        start_time = time.time()
        test_errors = []
        test_output = None
        
        try:
            if script.language.lower() == 'python':
                # For Python scripts, we'd need a more sophisticated execution environment
                # This is a simplified version
                result = self._execute_python_script(script.script_path, test_input, timeout_seconds)
                test_output = result.get('output')
                if result.get('errors'):
                    test_errors.extend(result['errors'])
            else:
                test_errors.append(f"Testing for {script.language} scripts not yet implemented")
                
        except Exception as e:
            test_errors.append(f"Script execution failed: {str(e)}")

        # 4. Calculate execution time
        execution_time = time.time() - start_time
        
        # 5. Determine test status
        test_status = 'passed' if not test_errors else 'failed'
        
        # 6. Update script test status in database
        try:
            self.script_crud.update_script(session, script_id, test_status=test_status)
        except:
            pass  # Don't fail the test if database update fails

        return {
            'script_id': script_id,
            'test_status': test_status,
            'execution_time': round(execution_time, 3),
            'test_output': test_output,
            'test_errors': test_errors
        }

    def _detect_script_language(self, content: str) -> str:
        """
        Detect programming language from script content
        """
        content_lower = content.lower().strip()
        
        if content_lower.startswith('#!/usr/bin/env python') or 'import ' in content_lower or 'def ' in content_lower:
            return 'python'
        elif content_lower.startswith('#!/bin/bash') or content_lower.startswith('#!/bin/sh'):
            return 'bash'
        elif 'function' in content_lower and '{' in content and '}' in content:
            return 'javascript'
        else:
            return 'python'  # Default to Python

    def _get_file_extension(self, language: str) -> str:
        """
        Get file extension for a programming language
        """
        extensions = {
            'python': '.py',
            'javascript': '.js',
            'bash': '.sh',
            'shell': '.sh',
            'sql': '.sql',
            'r': '.R'
        }
        return extensions.get(language.lower(), '.txt')

    def _execute_python_script(self, script_path: str, test_input: dict, timeout: int) -> dict:
        """
        Execute a Python script with test input (simplified implementation)
        """
        import subprocess
        import json
        
        try:
            # Convert test_input to JSON string for sys.argv[1]
            input_json_str = json.dumps(test_input)
            
            # Execute the script with JSON string as argument
            result = subprocess.run([
                'python', script_path, input_json_str
            ], capture_output=True, text=True, timeout=timeout)
            
            output = None
            errors = []
            
            if result.returncode == 0:
                try:
                    output = json.loads(result.stdout) if result.stdout.strip() else None
                except json.JSONDecodeError:
                    output = result.stdout
            else:
                errors.append(result.stderr)
                
            return {
                'output': output,
                'errors': errors
            }
            
        except subprocess.TimeoutExpired:
            return {
                'output': None,
                'errors': [f'Script execution timed out after {timeout} seconds']
            }
        except Exception as e:
            return {
                'output': None,
                'errors': [f'Execution error: {str(e)}']
            }

# ================================================================================================ WORKFLOW FUNCTIONS ==
    def create_workflow(self, session: Session, workflow_data: dict) -> dict:
        """
        Create a new workflow with nodes and edges if provided
        """
        # 1. Check if workflow name already exists
        existing_workflow = self.workflow_crud.get_by_name(session, workflow_data.get('name'))
        if existing_workflow:
            raise ValidationError(f"Workflow with name '{workflow_data.get('name')}' already exists")

        # 2. Validate workflow name (no special chars)
        name = workflow_data.get('name', '')
        if not name or len(name.strip()) < 3:
            raise ValidationError("Workflow name must be at least 3 characters long")

        # 3. Validate nodes and edges consistency
        nodes_data = workflow_data.get('nodes')
        edges_data = workflow_data.get('edges')
        
        if nodes_data is not None and edges_data is None:
            raise ValidationError("Nodes veriliyorsa edges de verilmeli")
        if edges_data is not None and nodes_data is None:
            raise ValidationError("Edges veriliyorsa nodes de verilmeli")
        if nodes_data is not None and edges_data is not None:
            if len(nodes_data) == 0 and len(edges_data) > 0:
                raise ValidationError("Node olmadan edge tanımlanamaz")

        # 4. Set default values
        from .models import WorkflowStatus
        db_workflow_data = {
            'name': name.strip(),
            'description': workflow_data.get('description', ''),
            'priority': workflow_data.get('priority', 50),  # Default priority
            'status': WorkflowStatus.DRAFT,  # Start as draft
        }

        # 5. Create workflow
        workflow = self.workflow_crud.create_workflow(session, **db_workflow_data)

        created_nodes_count = 0
        created_edges_count = 0

        # 6. Create nodes if provided
        if nodes_data is not None and len(nodes_data) > 0:
            node_id_mapping = {}  # Original node_id -> New node_id mapping
            
            for node_data in nodes_data:
                # Set workflow_id for the node
                node_create_data = dict(node_data)
                node_create_data['workflow_id'] = workflow.id
                
                # Store original node_id if exists (for edge creation)
                original_node_id = node_create_data.get('id')
                if 'id' in node_create_data:
                    del node_create_data['id']  # Remove id, let database generate
                
                # Create node
                created_node = self.node_crud.create_node(session, **node_create_data)
                created_nodes_count += 1
                
                # Store mapping for edge creation
                if original_node_id:
                    node_id_mapping[original_node_id] = created_node.id

        # 7. Create edges if provided
        if edges_data is not None and len(edges_data) > 0:
            for edge_data in edges_data:
                edge_create_data = dict(edge_data)
                edge_create_data['workflow_id'] = workflow.id
                
                # Map node IDs if mapping exists
                if node_id_mapping:
                    if edge_create_data.get('from_node_id') in node_id_mapping:
                        edge_create_data['from_node_id'] = node_id_mapping[edge_create_data['from_node_id']]
                    if edge_create_data.get('to_node_id') in node_id_mapping:
                        edge_create_data['to_node_id'] = node_id_mapping[edge_create_data['to_node_id']]
                
                # Remove id if exists
                if 'id' in edge_create_data:
                    del edge_create_data['id']
                
                # Create edge with full validation
                self.create_edge(session, edge_create_data)
                created_edges_count += 1

        # 8. Return API format
        return {
            'workflow_id': workflow.id,
            'name': workflow.name,
            'workflow_status': str(workflow.status),
            'created_at': workflow.created_at.isoformat() if workflow.created_at else None,
            'created_nodes_count': created_nodes_count if nodes_data else None,
            'created_edges_count': created_edges_count if edges_data else None
        }

    def update_workflow(self, session: Session, workflow_id: str, workflow_data: dict) -> dict:
        """
        Update an existing workflow with nodes and edges if provided
        """
        # 1. Find existing workflow
        workflow = self.workflow_crud.find_by_id(session, workflow_id)
        if not workflow:
            raise BusinessLogicError(f"Workflow not found: {workflow_id}")
        
        # 2. If name is being changed, check uniqueness
        if 'name' in workflow_data and workflow_data['name'] != workflow.name:
            existing_workflow = self.workflow_crud.get_by_name(session, workflow_data['name'])
            if existing_workflow and existing_workflow.id != workflow_id:
                raise ValidationError(f"Workflow with name '{workflow_data['name']}' already exists")
            
            # Validate new name
            name = workflow_data['name']
            if not name or len(name.strip()) < 3:
                raise ValidationError("Workflow name must be at least 3 characters long")

        # 3. Validate nodes and edges consistency
        nodes_data = workflow_data.get('nodes')
        edges_data = workflow_data.get('edges')
        
        if nodes_data is not None and edges_data is None:
            raise ValidationError("Nodes veriliyorsa edges de verilmeli")
        if edges_data is not None and nodes_data is None:
            raise ValidationError("Edges veriliyorsa nodes de verilmeli")
        if nodes_data is not None and edges_data is not None:
            if len(nodes_data) == 0 and len(edges_data) > 0:
                raise ValidationError("Node olmadan edge tanımlanamaz")

        # 4. Handle status changes with validation
        if 'status' in workflow_data:
            new_status = workflow_data['status']
            # Check if workflow can be activated (must have nodes)
            if new_status == 'active':
                nodes = self.node_crud.get_nodes_by_workflow(session, workflow_id)
                if not nodes:
                    raise BusinessLogicError("Cannot activate workflow - it has no nodes")

        # 5. Handle priority validation
        if 'priority' in workflow_data:
            priority = workflow_data['priority']
            if not isinstance(priority, int) or not (0 <= priority <= 100):
                raise ValidationError("Priority must be an integer between 0 and 100")

        updated_nodes_count = 0
        updated_edges_count = 0

        # 6. Handle nodes update if provided
        if nodes_data is not None:
            # Strategy: Replace all nodes (delete existing, create new)
            # Delete existing nodes (this will cascade to edges)
            existing_nodes = self.node_crud.get_nodes_by_workflow(session, workflow_id)
            for node in existing_nodes:
                self.delete_node(session, node.id, force=True)
            
            # Create new nodes
            node_id_mapping = {}
            for node_data in nodes_data:
                node_create_data = dict(node_data)
                node_create_data['workflow_id'] = workflow_id
                
                # Store original node_id if exists (for edge creation)
                original_node_id = node_create_data.get('id')
                if 'id' in node_create_data:
                    del node_create_data['id']
                
                # Create node
                created_node = self.node_crud.create_node(session, **node_create_data)
                updated_nodes_count += 1
                
                # Store mapping for edge creation
                if original_node_id:
                    node_id_mapping[original_node_id] = created_node.id

        # 7. Handle edges update if provided
        if edges_data is not None:
            # Strategy: Replace all edges (delete existing, create new)
            existing_edges = self.edge_crud.get_edges_by_workflow(session, workflow_id)
            for edge in existing_edges:
                self.delete_edge(session, edge.id)
            
            # Create new edges
            for edge_data in edges_data:
                edge_create_data = dict(edge_data)
                edge_create_data['workflow_id'] = workflow_id
                
                # Map node IDs if mapping exists
                if node_id_mapping:
                    if edge_create_data.get('from_node_id') in node_id_mapping:
                        edge_create_data['from_node_id'] = node_id_mapping[edge_create_data['from_node_id']]
                    if edge_create_data.get('to_node_id') in node_id_mapping:
                        edge_create_data['to_node_id'] = node_id_mapping[edge_create_data['to_node_id']]
                
                # Remove id if exists
                if 'id' in edge_create_data:
                    del edge_create_data['id']
                
                # Create edge with full validation
                self.create_edge(session, edge_create_data)
                updated_edges_count += 1

        # 8. Prepare workflow data for update (exclude nodes/edges)
        workflow_update_data = {k: v for k, v in workflow_data.items() 
                              if k not in ['nodes', 'edges']}

        # 9. Update workflow basic info
        updated_workflow = self.workflow_crud.update_workflow(session, workflow_id, **workflow_update_data)

        # 10. Return API format
        updated_fields = list(workflow_update_data.keys())
        if nodes_data is not None:
            updated_fields.append('nodes')
        if edges_data is not None:
            updated_fields.append('edges')
            
        return {
            'workflow_id': updated_workflow.id,
            'updated_fields': updated_fields,
            'updated_at': updated_workflow.updated_at.isoformat() if updated_workflow.updated_at else None,
            'updated_nodes_count': updated_nodes_count if nodes_data is not None else None,
            'updated_edges_count': updated_edges_count if edges_data is not None else None
        }

    def delete_workflow(self, session: Session, workflow_id: str, force: bool = False) -> dict:
        """
        Delete a workflow with dependency checking
        """
        # 1. Find workflow to delete
        workflow = self.workflow_crud.find_by_id(session, workflow_id)
        if not workflow:
            raise BusinessLogicError(f"Workflow not found: {workflow_id}")

        # 2. Check for running executions (unless force delete)
        if not force:
            running_executions = self.execution_crud.get_executions_by_workflow(session, workflow_id)
            running_count = len([e for e in running_executions if str(e.status) == 'running'])
            if running_count > 0:
                raise BusinessLogicError(f"Cannot delete workflow - it has {running_count} running execution(s). Use force=True to override.")

        # 3. Clean up dependent entities (nodes, edges, executions)
        # Delete nodes (which should cascade to edges)
        nodes = self.node_crud.get_nodes_by_workflow(session, workflow_id)
        for node in nodes:
            self.node_crud.delete_node(session, node.id)

        # Delete executions
        executions = self.execution_crud.get_executions_by_workflow(session, workflow_id)
        for execution in executions:
            self.execution_crud.delete_execution(session, execution.id)

        # 4. Delete the workflow
        deleted_workflow = self.workflow_crud.delete_workflow(session, workflow_id)

        # 5. Return API format
        return {
            'workflow_id': deleted_workflow.id,
            'workflow_name': deleted_workflow.name,
            'deleted_nodes': len(nodes),
            'deleted_executions': len(executions)
        }

    def validate_workflow(self, session: Session, workflow_id: str) -> dict:
        """
        Validate workflow configuration and integrity
        """
        # 1. Find workflow
        workflow = self.workflow_crud.find_by_id(session, workflow_id)
        if not workflow:
            raise BusinessLogicError(f"Workflow not found: {workflow_id}")

        validation_errors = []
        validation_warnings = []

        # 2. Validate name format
        name = workflow.name
        if not name or len(name.strip()) < 3:
            validation_errors.append("Workflow name must be at least 3 characters long")

        # 3. Check if workflow has nodes
        nodes = self.node_crud.get_nodes_by_workflow(session, workflow_id)
        if not nodes:
            validation_warnings.append("Workflow has no nodes")
        else:
            # 4. Check for disconnected nodes (nodes without edges)
            edges = self.edge_crud.get_edges_by_workflow(session, workflow_id)
            node_ids = {node.id for node in nodes}
            connected_nodes = set()
            
            for edge in edges:
                connected_nodes.add(edge.from_node_id)
                connected_nodes.add(edge.to_node_id)
            
            disconnected_nodes = node_ids - connected_nodes
            if disconnected_nodes and len(nodes) > 1:
                validation_warnings.append(f"Workflow has {len(disconnected_nodes)} disconnected node(s)")

            # 5. Check for circular dependencies
            if edges:
                try:
                    # Basic circular dependency check
                    for edge in edges:
                        if self._has_circular_dependency(session, edge.from_node_id, edge.to_node_id):
                            validation_errors.append("Workflow contains circular dependencies")
                            break
                except:
                    pass  # Skip if circular dependency check fails

        # 6. Check priority range
        if not (0 <= workflow.priority <= 100):
            validation_errors.append("Workflow priority must be between 0 and 100")

        # 7. Check if active workflow has proper configuration
        if str(workflow.status) == 'active':
            if not nodes:
                validation_errors.append("Active workflow must have at least one node")

        # 8. Return validation result
        is_valid = len(validation_errors) == 0
        return {
            'workflow_id': workflow_id,
            'is_valid': is_valid,
            'validation_errors': validation_errors,
            'validation_warnings': validation_warnings,
            'node_count': len(nodes),
            'edge_count': len(edges) if 'edges' in locals() else 0
        }

    def search_workflows(self, session: Session, search_criteria: dict) -> dict:
        """
        Search/filter workflows based on criteria
        """
        workflows = self.workflow_crud.search_workflows(session, **search_criteria)
        
        workflow_list = []
        for workflow in workflows:
            workflow_dict = workflow.to_dict()
            workflow_dict['workflow_id'] = workflow_dict['id']  # Add consistent field name
            
            # Add computed fields
            nodes = self.node_crud.get_nodes_by_workflow(session, workflow.id)
            edges = self.edge_crud.get_edges_by_workflow(session, workflow.id)
            workflow_dict['node_count'] = len(nodes)
            workflow_dict['edge_count'] = len(edges)
            
            # Add latest execution info
            latest_execution = self.execution_crud.get_latest_execution_for_workflow(session, workflow.id)
            if latest_execution:
                workflow_dict['last_execution_id'] = latest_execution.id
                workflow_dict['last_execution_status'] = str(latest_execution.status)
                if latest_execution.started_at and latest_execution.ended_at:
                    duration = (latest_execution.ended_at - latest_execution.started_at).total_seconds()
                    workflow_dict['last_execution_duration'] = duration
            
            workflow_list.append(workflow_dict)

        return {
            'message': 'Workflow search completed',
            'data': workflow_list,
            'total_count': len(workflow_list)
        }

    def get_workflows(self, session: Session, status: Optional[str] = None, 
                     is_active: Optional[bool] = None, page: Optional[int] = None, 
                     page_size: Optional[int] = None) -> dict:
        """
        List workflows with optional filtering
        """
        if status and is_active is not None:
            workflows = self.workflow_crud.filter(session, {'status': status, 'is_active': is_active})
        elif status:
            workflows = self.workflow_crud.get_by_status(session, status)
        elif is_active is not None:
            if is_active:
                workflows = self.workflow_crud.get_active_workflows(session)
            else:
                workflows = self.workflow_crud.get_inactive_workflows(session)
        else:
            skip = (page - 1) * page_size if page and page_size else 0
            limit = page_size if page_size else 100
            workflows = self.workflow_crud.get_all(session, skip=skip, limit=limit)
        
        workflow_list = []
        for workflow in workflows:
            workflow_dict = workflow.to_dict()
            workflow_dict['workflow_id'] = workflow_dict['id']  # Add consistent field name
            
            # Add computed fields
            nodes = self.node_crud.get_nodes_by_workflow(session, workflow.id)
            edges = self.edge_crud.get_edges_by_workflow(session, workflow.id)
            workflow_dict['node_count'] = len(nodes)
            workflow_dict['edge_count'] = len(edges)
            
            # Add execution statistics
            executions = self.execution_crud.get_executions_by_workflow(session, workflow.id)
            workflow_dict['execution_count'] = len(executions)
            
            # Add latest execution info
            if executions:
                latest_execution = max(executions, key=lambda e: e.started_at or e.created_at)
                workflow_dict['last_execution_id'] = latest_execution.id
                workflow_dict['last_execution_status'] = str(latest_execution.status)
                if latest_execution.started_at and latest_execution.ended_at:
                    duration = (latest_execution.ended_at - latest_execution.started_at).total_seconds()
                    workflow_dict['last_execution_duration'] = duration
            
            workflow_list.append(workflow_dict)

        return {
            'message': 'Workflows listed successfully',
            'data': workflow_list,
            'total_count': len(workflow_list)
        }

    def get_workflow(self, session: Session, workflow_id: str, include_nodes: bool = False, 
                    include_edges: bool = False) -> dict:
        """
        Get detailed information about a specific workflow
        """
        # 1. Find workflow
        workflow = self.workflow_crud.find_by_id(session, workflow_id)
        if not workflow:
            raise BusinessLogicError(f"Workflow not found: {workflow_id}")

        # 2. Prepare workflow data
        workflow_dict = workflow.to_dict()
        workflow_dict['workflow_id'] = workflow_dict['id']  # Add consistent field name

        # 3. Add computed fields
        nodes = self.node_crud.get_nodes_by_workflow(session, workflow_id)
        edges = self.edge_crud.get_edges_by_workflow(session, workflow_id)
        executions = self.execution_crud.get_executions_by_workflow(session, workflow_id)
        
        workflow_dict['node_count'] = len(nodes)
        workflow_dict['edge_count'] = len(edges)
        workflow_dict['execution_count'] = len(executions)

        # 4. Optionally include nodes and edges
        if include_nodes:
            workflow_dict['nodes'] = [node.to_dict() for node in nodes]
        
        if include_edges:
            workflow_dict['edges'] = [edge.to_dict() for edge in edges]

        # 5. Add latest execution info
        if executions:
            latest_execution = max(executions, key=lambda e: e.started_at or e.created_at)
            workflow_dict['last_execution_id'] = latest_execution.id
            workflow_dict['last_execution_status'] = str(latest_execution.status)
            if latest_execution.started_at and latest_execution.ended_at:
                duration = (latest_execution.ended_at - latest_execution.started_at).total_seconds()
                workflow_dict['last_execution_duration'] = duration

        return {
            'message': 'Workflow retrieved successfully',
            'data': workflow_dict
        }

    def count_workflows(self, session: Session, group_by: Optional[str] = None) -> dict:
        """
        Count workflows with optional grouping
        """
        total_count = self.workflow_crud.count(session)
        
        result = {
            'message': 'Workflow count retrieved successfully',
            'workflow_count': total_count
        }
        
        if group_by == 'status':
            status_counts = self.workflow_crud.count_by_status(session)
            result['by_status'] = status_counts
        elif group_by == 'activity':
            active_count = len(self.workflow_crud.get_active_workflows(session))
            inactive_count = total_count - active_count
            result['by_activity'] = {'active': active_count, 'inactive': inactive_count}

        return result

    def workflow_exists(self, session: Session, workflow_id: str) -> dict:
        """
        Check if a workflow exists
        """
        exists = self.workflow_crud.exists(session, workflow_id)
        
        return {
            'message': 'Workflow existence checked',
            'is_exists': exists
        }

    def run_workflow(self, session: Session, workflow_id: str) -> dict:
        """
        Trigger workflow execution - creates execution and execution inputs with dependency calculation
        """
        result = self.trigger_workflow(session, workflow_id)
        
        # Reformat to match API expectations
        return {
            'workflow_id': workflow_id,
            'execution_id': result.get('execution_id'),
            'message': 'Workflow execution started'
        }

    def trigger_workflow(self, session: Session, workflow_id: str) -> dict:
        """
        Trigger workflow execution by creating execution and execution inputs with dependency calculation
        """
        # 1. Validate workflow exists
        workflow = self.workflow_crud.find_by_id(session, workflow_id)
        if not workflow:
            raise BusinessLogicError(f"Workflow not found: {workflow_id}")

        # 2. Get all nodes for this workflow
        nodes = self.node_crud.get_nodes_by_workflow(session, workflow_id)
        if not nodes:
            raise BusinessLogicError(f"Cannot trigger workflow - no nodes found: {workflow_id}")

        # 3. Get all edges for this workflow
        edges = self.edge_crud.get_edges_by_workflow(session, workflow_id)

        # 4. Create execution record
        from datetime import datetime
        from .models import ExecutionStatus
        
        db_execution_data = {
            'workflow_id': workflow_id,
            'status': ExecutionStatus.PENDING,
            'pending_nodes': len(nodes),
            'executed_nodes': 0,
            'started_at': datetime.utcnow(),  # Mark as started when triggered
            'ended_at': None
        }

        execution = self.execution_crud.create_execution(session, **db_execution_data)

        # 5. Calculate dependencies for each node
        node_dependencies = {}
        for node in nodes:
            # Count incoming edges (dependencies)
            dependency_count = 0
            for edge in edges:
                if edge.to_node_id == node.id:
                    dependency_count += 1
            node_dependencies[node.id] = dependency_count

        # 6. Create execution inputs for all nodes
        created_inputs = 0
        try:
            for node in nodes:
                # Resolve environment variables in node parameters
                resolved_node_params = self._resolve_dynamic_parameters(
                    session, execution.id, node.params or {}
                ) if node.params else {}
                
                execution_input_data = {
                    'execution_id': execution.id,
                    'node_id': node.id,
                    'dependency_count': node_dependencies[node.id],
                    'node_name': node.name,  # Required field
                    'script_path': node.script.script_path if node.script else None,  # Denormalized for performance
                    'node_params': resolved_node_params  # Resolved environment variables
                }

                self.execution_input_crud.create_execution_input(session, **execution_input_data)
                created_inputs += 1
        except Exception as e:
            # If execution input creation fails, rollback the execution too
            print(f"[ORCHESTRATION] ERROR creating execution inputs: {str(e)}")
            import traceback
            traceback.print_exc()
            session.rollback()
            raise BusinessLogicError(f"Failed to create execution inputs: {str(e)}")

        # 7. Return result
        return {
            'execution_id': execution.id,
            'workflow_id': workflow_id,
            'total_nodes': len(nodes),
            'ready_nodes': len([dep for dep in node_dependencies.values() if dep == 0]),
            'created_inputs': created_inputs,
            'message': f'Workflow triggered: {created_inputs} execution inputs created'
        }

    def clone_workflow(self, session: Session, workflow_id: str, clone_data: dict) -> dict:
        """
        Clone an existing workflow with all its components
        """
        from datetime import datetime
        
        # 1. Find source workflow
        source_workflow = self.workflow_crud.find_by_id(session, workflow_id)
        if not source_workflow:
            raise BusinessLogicError(f"Source workflow not found: {workflow_id}")

        # 2. Prepare new workflow data
        new_name = clone_data.get('new_name')
        if not new_name:
            raise ValidationError("new_name is required for cloning")

        # Check if new name already exists
        if self.workflow_crud.get_by_name(session, new_name):
            raise ValidationError(f"Workflow with name '{new_name}' already exists")

        # 3. Create new workflow
        from .models import WorkflowStatus
        new_workflow_data = {
            'name': new_name,
            'description': clone_data.get('new_description', f"Cloned from {source_workflow.name}"),
            'priority': source_workflow.priority,
            'status': WorkflowStatus.DRAFT  # Always start cloned workflows as draft
        }
        
        new_workflow = self.workflow_crud.create_workflow(session, **new_workflow_data)

        cloned_components = {'nodes': 0, 'edges': 0, 'executions': 0}

        # 4. Clone nodes if requested
        if clone_data.get('include_nodes', True):
            source_nodes = self.node_crud.get_nodes_by_workflow(session, workflow_id)
            node_id_mapping = {}  # Map old node IDs to new node IDs
            
            for source_node in source_nodes:
                node_data = {
                    'name': source_node.name,
                    'description': source_node.description,
                    'script_id': source_node.script_id,
                    'workflow_id': new_workflow.id,
                    'node_params': source_node.node_params
                }
                new_node = self.node_crud.create_node(session, **node_data)
                node_id_mapping[source_node.id] = new_node.id
                cloned_components['nodes'] += 1

            # 5. Clone edges if requested
            if clone_data.get('include_edges', True):
                source_edges = self.edge_crud.get_edges_by_workflow(session, workflow_id)
                for source_edge in source_edges:
                    if (source_edge.from_node_id in node_id_mapping and 
                        source_edge.to_node_id in node_id_mapping):
                        edge_data = {
                            'workflow_id': new_workflow.id,
                            'from_node_id': node_id_mapping[source_edge.from_node_id],
                            'to_node_id': node_id_mapping[source_edge.to_node_id],
                            'condition_type': source_edge.condition_type
                        }
                        self.edge_crud.create_edge(session, **edge_data)
                        cloned_components['edges'] += 1

        # 6. Return clone result
        return {
            'source_workflow_id': workflow_id,
            'new_workflow_id': new_workflow.id,
            'new_workflow_name': new_workflow.name,
            'cloned_at': datetime.utcnow().isoformat(),
            'cloned_components': cloned_components,
            'message': 'Workflow cloned successfully'
        }

# ============================================================================================== EXECUTION MANAGEMENT FUNCTIONS ==
    def create_execution(self, session: Session, execution_data: dict) -> dict:
        """
        Create a new execution and trigger workflow execution with dependency calculation
        """
        # 1. Validate workflow exists
        workflow_id = execution_data.get('workflow_id')
        workflow = self.workflow_crud.find_by_id(session, workflow_id)
        if not workflow:
            raise BusinessLogicError(f"Workflow not found: {workflow_id}")

        # 2. Use trigger_workflow to create execution + execution inputs
        result = self.trigger_workflow(session, workflow_id)

        # 3. Return API format with additional trigger info
        from datetime import datetime
        return {
            'execution_id': result['execution_id'],
            'workflow_id': workflow_id,
            'status': 'pending',
            'total_nodes': result['total_nodes'],
            'ready_nodes': result['ready_nodes'],
            'created_inputs': result['created_inputs'],
            'created_at': datetime.utcnow().isoformat(),
            'message': 'Execution created and workflow triggered'
        }

    def update_execution(self, session: Session, execution_id: str, execution_data: dict) -> dict:
        """
        Update execution details (limited updates allowed)
        """
        # 1. Find existing execution
        execution = self.execution_crud.find_by_id(session, execution_id)
        if not execution:
            raise BusinessLogicError(f"Execution not found: {execution_id}")
        
        # 2. Validate update restrictions
        from .models import ExecutionStatus
        if execution.status in [ExecutionStatus.COMPLETED, ExecutionStatus.FAILED]:
            raise BusinessLogicError("Cannot update completed or failed executions")

        # 3. Prepare allowed updates
        allowed_fields = ['results']  # Only certain fields can be updated
        update_data = {k: v for k, v in execution_data.items() if k in allowed_fields}

        if not update_data:
            raise ValidationError("No valid fields to update")

        # 4. Update execution
        updated_execution = self.execution_crud.update_execution(session, execution_id, **update_data)

        # 5. Return API format
        updated_fields = list(update_data.keys())
        return {
            'execution_id': updated_execution.id,
            'updated_fields': updated_fields,
            'updated_at': updated_execution.updated_at.isoformat() if updated_execution.updated_at else None
        }

    def delete_execution(self, session: Session, execution_id: str, force: bool = False) -> dict:
        """
        Delete an execution (with restrictions)
        """
        # 1. Find execution to delete
        execution = self.execution_crud.find_by_id(session, execution_id)
        if not execution:
            raise BusinessLogicError(f"Execution not found: {execution_id}")
        
        # 2. Check if execution can be deleted
        from .models import ExecutionStatus
        if not force and execution.status == ExecutionStatus.RUNNING:
            raise BusinessLogicError("Cannot delete running execution. Cancel it first or use force=True")

        # 3. Clean up related data (execution inputs/outputs)
        # Note: In a real implementation, we'd clean up execution_inputs and execution_outputs

        # 4. Delete execution
        deleted_execution = self.execution_crud.delete_execution(session, execution_id)

        # 5. Return API format
        return {
            'execution_id': deleted_execution.id,
            'workflow_id': deleted_execution.workflow_id,
            'was_running': execution.status == ExecutionStatus.RUNNING
        }

    def validate_execution(self, session: Session, execution_id: str) -> dict:
        """
        Validate execution configuration and state
        """
        # 1. Find execution
        execution = self.execution_crud.find_by_id(session, execution_id)
        if not execution:
            raise BusinessLogicError(f"Execution not found: {execution_id}")

        validation_errors = []
        validation_warnings = []

        # 2. Validate workflow still exists
        workflow = self.workflow_crud.find_by_id(session, execution.workflow_id)
        if not workflow:
            validation_errors.append("Associated workflow no longer exists")
        else:
            # 3. Check workflow integrity
            nodes = self.node_crud.get_nodes_by_workflow(session, execution.workflow_id)
            if not nodes:
                validation_errors.append("Workflow has no nodes")
            
            if execution.pending_nodes != len(nodes) and execution.status.value == 'pending':
                validation_warnings.append(f"Pending nodes count mismatch: expected {len(nodes)}, got {execution.pending_nodes}")

        # 4. Validate execution state consistency
        from .models import ExecutionStatus
        if execution.status == ExecutionStatus.RUNNING and not execution.started_at:
            validation_errors.append("Running execution missing start timestamp")
        
        if execution.status in [ExecutionStatus.COMPLETED, ExecutionStatus.FAILED, ExecutionStatus.CANCELLED]:
            if not execution.ended_at:
                validation_warnings.append("Finished execution missing end timestamp")

        # 5. Check node counts consistency
        total_nodes = execution.pending_nodes + execution.executed_nodes
        if workflow and nodes and total_nodes != len(nodes):
            validation_warnings.append(f"Node count inconsistency: total={total_nodes}, workflow_nodes={len(nodes)}")

        # 6. Return validation result
        is_valid = len(validation_errors) == 0
        return {
            'execution_id': execution_id,
            'is_valid': is_valid,
            'validation_errors': validation_errors,
            'validation_warnings': validation_warnings
        }

    def search_executions(self, session: Session, search_criteria: dict) -> dict:
        """
        Search/filter executions based on criteria
        """
        executions = self.execution_crud.search_executions(session, **search_criteria)
        
        execution_list = []
        for execution in executions:
            execution_dict = execution.to_dict()
            execution_dict['execution_id'] = execution_dict['id']  # Add consistent field name
            
            # Add computed duration if available
            if execution.started_at:
                duration = self.execution_crud.get_execution_duration(session, execution.id)
                execution_dict['duration_seconds'] = duration
            
            execution_list.append(execution_dict)

        return {
            'message': 'Execution search completed',
            'data': execution_list,
            'total_count': len(execution_list)
        }

    def get_executions_list(self, session: Session, workflow_id: Optional[str] = None, 
                      status: Optional[str] = None, page: Optional[int] = None, 
                      page_size: Optional[int] = None) -> dict:
        """
        List executions with optional filtering
        """
        if workflow_id and status:
            executions = self.execution_crud.filter(session, {'workflow_id': workflow_id, 'status': status})
        elif workflow_id:
            executions = self.execution_crud.get_executions_by_workflow(session, workflow_id)
        elif status:
            executions = self.execution_crud.get_executions_by_status(session, status)
        else:
            skip = (page - 1) * page_size if page and page_size else 0
            limit = page_size if page_size else 100
            executions = self.execution_crud.get_all(session, skip=skip, limit=limit)
        
        execution_list = []
        for execution in executions:
            execution_dict = execution.to_dict()
            execution_dict['execution_id'] = execution_dict['id']  # Add consistent field name
            
            # Add computed duration if available
            if execution.started_at:
                duration = self.execution_crud.get_execution_duration(session, execution.id)
                execution_dict['duration_seconds'] = duration
            
            execution_list.append(execution_dict)

        return {
            'message': 'Executions listed successfully',
            'data': execution_list,
            'total_count': len(execution_list)
        }

    def get_execution_detail(self, session: Session, execution_id: str, include_results: bool = False) -> dict:
        """
        Get detailed information about a specific execution
        """
        # 1. Find execution
        execution = self.execution_crud.find_by_id(session, execution_id)
        if not execution:
            raise BusinessLogicError(f"Execution not found: {execution_id}")
        
        # 2. Prepare execution data
        execution_dict = execution.to_dict()
        execution_dict['execution_id'] = execution_dict['id']  # Add consistent field name

        # 3. Add computed fields
        if execution.started_at:
            duration = self.execution_crud.get_execution_duration(session, execution_id)
            execution_dict['duration_seconds'] = duration

        # 4. Add workflow information
        workflow = self.workflow_crud.find_by_id(session, execution.workflow_id)
        if workflow:
            execution_dict['workflow_name'] = workflow.name

        # 5. Optionally include results
        if not include_results and 'results' in execution_dict:
            execution_dict['results'] = '***HIDDEN***'  # Hide sensitive results

        return {
            'message': 'Execution retrieved successfully',
            'data': execution_dict
        }

    def count_executions(self, session: Session, group_by: Optional[str] = None) -> dict:
        """
        Count executions with optional grouping
        """
        total_count = self.execution_crud.count(session)
        
        result = {
            'message': 'Execution count retrieved successfully',
            'execution_count': total_count
        }
        
        if group_by == 'status':
            status_counts = self.execution_crud.count_by_status(session)
            result['by_status'] = status_counts
        elif group_by == 'workflow':
            workflow_counts = self.execution_crud.count_by_workflow(session)
            result['by_workflow'] = workflow_counts
        elif group_by == 'both':
            result['by_status'] = self.execution_crud.count_by_status(session)
            result['by_workflow'] = self.execution_crud.count_by_workflow(session)

        return result

    def execution_exists_check(self, session: Session, execution_id: str) -> dict:
        """
        Check if an execution exists
        """
        exists = self.execution_crud.exists(session, execution_id)

        return {
            'message': 'Execution existence checked',
            'is_exists': exists
        }

    def get_execution_results(self, session: Session, execution_id: str) -> dict:
        """
        Get execution results
        """
        # 1. Find execution
        execution = self.execution_crud.find_by_id(session, execution_id)
        if not execution:
            raise BusinessLogicError(f"Execution not found: {execution_id}")

        # 2. Check if execution has results
        from .models import ExecutionStatus
        if execution.status not in [ExecutionStatus.COMPLETED, ExecutionStatus.FAILED, ExecutionStatus.CANCELLED]:
            return {
                'execution_id': execution_id,
                'status': str(execution.status),
                'results': None,
                'message': 'Execution not yet finished'
            }

        # 3. Return results
        return {
            'execution_id': execution_id,
            'status': str(execution.status),
            'results': execution.results or {},
            'message': 'Execution results retrieved successfully'
        }

    def get_execution_status(self, session: Session, execution_id: str) -> dict:
        """
        Get current execution status
        """
        # 1. Find execution
        execution = self.execution_crud.find_by_id(session, execution_id)
        if not execution:
            raise BusinessLogicError(f"Execution not found: {execution_id}")

        # 2. Calculate progress
        total_nodes = execution.pending_nodes + execution.executed_nodes
        progress_percentage = 0
        if total_nodes > 0:
            progress_percentage = (execution.executed_nodes / total_nodes) * 100

        # 3. Calculate duration
        duration = None
        if execution.started_at:
            duration = self.execution_crud.get_execution_duration(session, execution_id)

        return {
            'execution_id': execution_id,
            'status': str(execution.status),
            'pending_nodes': execution.pending_nodes,
            'executed_nodes': execution.executed_nodes,
            'progress_percentage': round(progress_percentage, 2),
            'duration_seconds': duration,
            'started_at': execution.started_at.isoformat() if execution.started_at else None,
            'ended_at': execution.ended_at.isoformat() if execution.ended_at else None
        }

    def cancel_execution_new(self, session: Session, execution_id: str, cancel_data: dict = None) -> dict:
        """
        Cancel a running execution (wrapper for existing function)
        """
        # Use the existing cancel_execution function which is already implemented
        # This is already in orchestration.py as part of the execution management
        existing_result = self.cancel_execution(session, execution_id)
        
        # Reformat to match API expectations
        return {
            'execution_id': existing_result.get('execution_id', execution_id),
            'results': existing_result.get('results', {}),
            'message': 'Execution cancelled successfully'
        }

# END-TO-END SCHEDULER FUNCTIONS
# ==============================================================
    def get_ready_tasks(self, session: Session, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get ready tasks for execution (dependency_count = 0)
        Returns enriched task data with node and execution info
        """
        return self.execution_input_crud.get_ready_tasks_with_details(session, limit)

    def remove_completed_tasks(self, session: Session, task_ids: List[str]) -> int:
        """
        Bulk remove completed tasks from execution_inputs table
        """
        return self.execution_input_crud.bulk_delete_by_ids(session, task_ids)

    def create_task_payload(self, session: Session, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create execution payload for parallelism engine
        1. Extract dynamic node params
        2. Split variable references  
        3. Get execution results from output table
        4. Build complete execution context
        """
        try:
            # Extract basic task information
            execution_id = task['execution_id']
            node_id = task['node_id']
            node_name = task['node_name']
            script_path = task['script_path']
            node_params = task['node_params'] or {}
            
            # Resolve dynamic parameters
            resolved_params = self._resolve_dynamic_parameters(
                session, execution_id, node_params
            )
            
            # Create the execution payload
            payload = {
                'id': task['task_id'],  # Use task_id as unique identifier
                'execution_id': execution_id,
                'node_id': node_id,
                'node_name': node_name,
                'script_path': script_path,
                'context': resolved_params,
                'max_retries': task.get('max_retries', 3),
                'timeout_seconds': task.get('timeout_seconds', 300),
                'workflow_id': task['workflow_id']
            }
            
            return payload
            
        except Exception as e:
            # Log error and return None to indicate failure
            print(f"[ORCHESTRATION] Error creating payload for task {task.get('task_id', 'unknown')}: {e}")
            return None

    def _resolve_dynamic_parameters(self, session: Session, execution_id: str, 
                                  node_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Resolve dynamic parameters in node_params
        Supports three formats:
        1. {{node_name.variable_name}} - Template format  
        2. node_name.variable_name - Direct format
        3. {{$variable_name}} - Environment variable format
        """
        if not node_params:
            return {}
            
        resolved_params = {}
        
        # First, extract {{}} format dynamic parameters and environment variables
        from ..utils import extract_dynamic_node_params, extract_env_var_params
        template_params = extract_dynamic_node_params(node_params)
        env_var_params = extract_env_var_params(node_params)
        
        for param_key, param_value in node_params.items():
            try:
                # Check if this parameter is an environment variable {{$var_name}}
                if param_key in env_var_params:
                    env_var_name = env_var_params[param_key]
                    resolved_value = self._resolve_environment_variable(session, env_var_name)
                    resolved_params[param_key] = resolved_value
                    
                # Check if this parameter has a template format {{node_name.variable_name}}
                elif param_key in template_params:
                    # Use the extracted value (already cleaned from {{}})
                    reference = template_params[param_key]
                    resolved_value = self._resolve_single_reference(session, execution_id, reference)
                    resolved_params[param_key] = resolved_value
                    
                # Check if this is a direct format (node_name.variable_name)
                elif isinstance(param_value, str) and '.' in param_value:
                    # Additional check: avoid treating simple filenames as dynamic references
                    # Dynamic references should not contain common file extensions
                    common_extensions = {'.txt', '.json', '.csv', '.xml', '.py', '.js', '.html', '.css', '.jpg', '.png',
                                         '.pdf'}
                    is_dynamic = True
                    
                    # Check if it ends with a common file extension
                    for ext in common_extensions:
                        if param_value.lower().endswith(ext):
                            is_dynamic = False
                            break
                    
                    # Also check for URL patterns (http://, https://, ftp://)
                    if param_value.startswith(('http://', 'https://', 'ftp://', 'file://')):
                        is_dynamic = False
                    
                    # Also exclude paths that contain multiple dots (like version numbers)
                    if param_value.count('.') > 1:
                        is_dynamic = False
                    
                    if is_dynamic:
                        resolved_value = self._resolve_single_reference(session, execution_id, param_value)
                        resolved_params[param_key] = resolved_value
                    else:
                        # Treat as static parameter
                        resolved_params[param_key] = param_value
                        
                else:
                    # Static parameter (no template, no direct format)
                    resolved_params[param_key] = param_value
                    
            except Exception as e:
                # On any error, use original value
                print(f"[ORCHESTRATION] Error resolving parameter {param_key}: {e}")
                resolved_params[param_key] = param_value
                
        return resolved_params

    def _resolve_environment_variable(self, session: Session, env_var_name: str) -> Any:
        """
        Resolve environment variable from the database environment_variables table
        Returns the resolved value or raises an error if not found
        """
        try:
            # Get environment variable from database
            env_var = self.env_var_crud.get_by_name(session, env_var_name)
            
            if not env_var:
                raise BusinessLogicError(f"Environment variable '{env_var_name}' not found in database")
            
            # Get the environment variable value (no encryption in simplified implementation)
            resolved_value = env_var.value
            
            print(f"[ORCHESTRATION] Resolved environment variable {env_var_name} = {resolved_value}")
            return resolved_value
            
        except Exception as e:
            print(f"[ORCHESTRATION] Error resolving environment variable {env_var_name}: {e}")
            # Return the original reference if resolution fails
            return f"${{${env_var_name}}}"
    
    def _resolve_single_reference(self, session: Session, execution_id: str, reference: str) -> Any:
        """
        Resolve a single dynamic reference (node_name.variable_name)
        Returns the resolved value or original reference if not found
        """
        try:
            from ..utils import split_variable_reference
            referenced_node_name, variable_name = split_variable_reference(reference)
            
            # Get the result data from the referenced node
            result_data = self.execution_output_crud.get_node_result_data(
                session, execution_id, referenced_node_name
            )
            
            if result_data and variable_name in result_data:
                return result_data[variable_name]
            else:
                # If reference not found, return original reference
                print(f"[ORCHESTRATION] Dynamic reference not found: {reference}")
                return reference
                
        except Exception as e:
            print(f"[ORCHESTRATION] Error resolving reference {reference}: {e}")
            return reference

    def process_execution_result(self, session: Session, result: Dict[str, Any]) -> bool:
        """
        Process single execution result
        1. Create execution_output record
        2. Update dependency counts for dependent nodes (if success)
        3. Update execution progress
        4. Handle failure by cancelling pending tasks (if failed)
        5. Check for workflow completion
        """
        try:
            execution_id = result.get('execution_id')
            node_id = result.get('node_id')
            status = result.get('status')  # 'success' or 'failed'
            result_data = result.get('result_data') or result.get('results', {})
            
            if not all([execution_id, node_id, status]):
                print(f"[ORCHESTRATION] Missing required fields in result: {result}")
                return False
            
            # Convert status to ExecutionOutputStatus enum
            from .models import ExecutionOutputStatus
            output_status = (
                ExecutionOutputStatus.SUCCESS if status == 'success' 
                else ExecutionOutputStatus.FAILURE
            )
            
            # Check if output already exists (idempotency)
            if self.execution_output_crud.check_output_exists(session, execution_id, node_id):
                print(f"[ORCHESTRATION] Output already exists for execution {execution_id}, node {node_id}")
                return True
            
            # Create execution output record
            self.execution_output_crud.create_execution_output(
                session=session,
                execution_id=execution_id,
                node_id=node_id,
                status=output_status,
                result_data=result_data,
                started_at=datetime.utcnow(),  # Could be passed from result
                ended_at=datetime.utcnow()
            )
            
            # Update execution progress
            self.execution_crud.increment_executed_nodes(session, execution_id)
            
            # Mark execution as running if it was pending
            self.execution_crud.mark_execution_running(session, execution_id)
            
            # Handle success vs failure differently
            if status == 'success':
                # Update dependent tasks only if this node succeeded
                self._update_dependent_tasks(session, node_id, execution_id)
                
                # Check if this is the last node and collect final results
                if self._is_last_node(session, node_id):
                    print(f"[ORCHESTRATION] Last node {node_id} completed successfully, collecting final results")
                    self._collect_final_results(session, execution_id)
                    
            else:
                # Handle node failure - cancel all pending tasks
                print(f"[ORCHESTRATION] Node {node_id} failed, cancelling remaining tasks in execution {execution_id}")
                self._handle_node_failure(session, execution_id, node_id)
            
            # Check for workflow completion
            if self.execution_crud.check_execution_completion(session, execution_id):
                self._complete_execution(session, execution_id)
            
            return True
            
        except Exception as e:
            print(f"[ORCHESTRATION] Error processing execution result: {e}")
            return False

    def _handle_node_failure(self, session: Session, execution_id: str, failed_node_id: str) -> int:
        """
        Handle node failure by cancelling all pending tasks in the execution
        Returns number of cancelled tasks
        """
        try:
            from .models import ExecutionOutputStatus
            
            # Get all remaining pending tasks for this execution
            pending_tasks = self.execution_input_crud.get_execution_inputs_by_execution(session, execution_id)
            
            if not pending_tasks:
                print(f"[ORCHESTRATION] No pending tasks to cancel for execution {execution_id}")
                return 0
            
            # Get task IDs to cancel
            task_ids_to_cancel = [task.id for task in pending_tasks]
            
            # Create CANCELLED outputs for all pending tasks
            for task in pending_tasks:
                # Create cancelled output record
                self.execution_output_crud.create_execution_output(
                    session=session,
                    execution_id=execution_id,
                    node_id=task.node_id,
                    status=ExecutionOutputStatus.CANCELLED,
                    result_data={'reason': f'Cancelled due to failure of node {failed_node_id}'},
                    started_at=datetime.utcnow(),
                    ended_at=datetime.utcnow()
                )
            
            # Remove all pending tasks from execution_inputs
            cancelled_count = self.execution_input_crud.bulk_delete_by_ids(session, task_ids_to_cancel)
            
            # Update execution pending_nodes count to 0 (since all remaining are cancelled)
            self.execution_crud.update_execution_progress(
                session=session,
                execution_id=execution_id,
                pending_nodes=0
            )
            
            print(f"[ORCHESTRATION] Cancelled {cancelled_count} pending tasks due to node failure")
            return cancelled_count
            
        except Exception as e:
            print(f"[ORCHESTRATION] Error handling node failure: {e}")
            return 0

    def _collect_final_results(self, session: Session, execution_id: str) -> Dict[str, Any]:
        """
        Collect final results when last node completes successfully
        Updates execution.results with comprehensive final results
        """
        try:
            # Use the enhanced combine method to get comprehensive results
            final_results = self.__combine_execution_results(session, execution_id)
            
            # Update execution with final results  
            execution = self.execution_crud.find_by_id(session, execution_id)
            execution.results = final_results
            execution.updated_at = datetime.utcnow()
            session.flush()
            
            print(f"[ORCHESTRATION] Final results collected and saved for execution {execution_id}")
            print(f"[ORCHESTRATION] Results summary: {final_results['summary']}")
            
            return final_results
            
        except Exception as e:
            print(f"[ORCHESTRATION] Error collecting final results: {e}")
            return {}

    def _is_last_node(self, session: Session, node_id: str) -> bool:
        """
        Check if a node is the last node (has no outgoing edges/downstream nodes)
        Returns True if this is a terminal node
        """
        try:
            # Check if this node has any outgoing edges
            from .models import Edge
            stmt = (
                select(func.count(Edge.id))
                .where(Edge.from_node_id == node_id)
            )
            
            outgoing_edge_count = session.execute(stmt).scalar_one()
            
            # If no outgoing edges, it's a last node
            is_last = outgoing_edge_count == 0
            
            if is_last:
                print(f"[ORCHESTRATION] Node {node_id} is identified as a last node (no downstream dependencies)")
            
            return is_last
            
        except Exception as e:
            print(f"[ORCHESTRATION] Error checking if node is last: {e}")
            return False

    def _update_dependent_tasks(self, session: Session, completed_node_id: str, 
                               execution_id: str) -> List[str]:
        """
        Update dependency counts for nodes dependent on completed node
        Returns list of newly ready task IDs
        """
        try:
            # Get dependent node IDs
            dependent_node_ids = self.execution_input_crud.get_dependent_nodes(
                session, completed_node_id, execution_id
            )
            
            if not dependent_node_ids:
                return []
            
            # Decrease dependency count for dependent nodes
            updated_count = self.execution_input_crud.decrease_dependency_count_for_nodes(
                session, dependent_node_ids, execution_id
            )
            
            print(f"[ORCHESTRATION] Updated {updated_count} dependent tasks")
            return dependent_node_ids
            
        except Exception as e:
            print(f"[ORCHESTRATION] Error updating dependent tasks: {e}")
            return []

    def _complete_execution(self, session: Session, execution_id: str) -> None:
        """
        Complete the execution and gather final results
        """
        try:
            # Get execution progress
            progress = self.execution_output_crud.get_execution_progress(session, execution_id)
            
            # Determine final status based on results
            final_status = ExecutionStatus.COMPLETED
            if progress['failure'] > 0 or progress['timeout'] > 0:
                final_status = ExecutionStatus.FAILED
            elif progress['cancelled'] > 0:
                final_status = ExecutionStatus.CANCELLED
            
            # Mark execution as complete
            self.execution_crud.mark_execution_completed(
                session=session,
                execution_id=execution_id,
                final_status=final_status,
                results=progress,
                ended_at=datetime.utcnow()
            )
            
            print(f"[ORCHESTRATION] Execution {execution_id} completed with status {final_status.value}")
            
        except Exception as e:
            print(f"[ORCHESTRATION] Error completing execution {execution_id}: {e}")

    def process_execution_results_batch(self, session: Session, 
                                       results: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Process multiple execution results in batch
        Returns success/failure counts
        """
        success_count = 0
        failure_count = 0
        
        for result in results:
            try:
                if self.process_execution_result(session, result):
                    success_count += 1
                else:
                    failure_count += 1
            except Exception as e:
                print(f"[ORCHESTRATION] Error in batch processing: {e}")
                failure_count += 1
        
        return {
            'success': success_count,
            'failure': failure_count,
            'total': len(results)
        }

    def __combine_execution_results(self, session: Session, execution_id: str) -> Dict[str, Any]:
        """
        Combine all node execution results into a comprehensive final result
        Returns both summary statistics and individual node results
        """
        try:
            # Get execution progress summary
            progress = self.execution_output_crud.get_execution_progress(session, execution_id)
            
            # Get all execution outputs with node information
            outputs = self.execution_output_crud.filter(session, {'execution_id': execution_id})
            
            # Build comprehensive node results dictionary
            node_results = {}
            execution_flow = []
            
            for output in outputs:
                # Get node name for proper identification
                node = self.node_crud.find_by_id(session, output.node_id)
                node_name = node.name if node else f"node_{output.node_id}"
                
                # Store result data by node name
                if output.result_data:
                    node_results[node_name] = output.result_data
                    
                    # Track execution flow
                    execution_flow.append({
                        'node_name': node_name,
                        'node_id': output.node_id,
                        'status': output.status.value,
                        'started_at': output.started_at.isoformat() if output.started_at else None,
                        'ended_at': output.ended_at.isoformat() if output.ended_at else None,
                        'has_result': bool(output.result_data)
                    })
            
            # Sort execution flow by start time
            execution_flow.sort(key=lambda x: x['started_at'] or '')
            
            # Build comprehensive final results
            final_results = {
                'summary': progress,
                'node_results': node_results,
                'execution_flow': execution_flow,
                'total_nodes': len(outputs),
                'consolidated_at': datetime.utcnow().isoformat(),
                'execution_id': execution_id
            }
            
            print(f"[ORCHESTRATION] Combined results for {len(outputs)} nodes")
            
            return final_results
            
        except Exception as e:
            print(f"[ORCHESTRATION] Error combining execution results: {e}")
            # Return minimal results if combination fails
            progress = self.execution_output_crud.get_execution_progress(session, execution_id)
            return {
                'summary': progress,
                'node_results': {},
                'error': str(e),
                'execution_id': execution_id
            }