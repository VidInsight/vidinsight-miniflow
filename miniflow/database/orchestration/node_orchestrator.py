# orchestration/node_orchestrator.py
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, Union, List

from .base_orchestration import BaseOrchestration
from ...exceptions import ValidationError, BusinessLogicError, ErrorManager


class NodeOrchestrator(BaseOrchestration):
    """Node operasyonları için orchestrator"""

    def __init__(self):
        super().__init__()

    def create(self, session: Session, node_data: Dict[str, Any]) -> Dict[str, Any]:
        """Node oluşturma"""
        # 1. VALIDATION: Workflow ID
        workflow_id = node_data.get('workflow_id')
        if not workflow_id:
            raise ValidationError("Workflow ID is required")
            
        workflow = self.workflow_crud.find_by_id(session, workflow_id)
        if not workflow:
            raise BusinessLogicError(f"Workflow not found: {workflow_id}")

        # 2. VALIDATION: Script ID (if provided)
        script_id = node_data.get('script_id')
        if script_id:  # Only validate if script_id is provided (it's nullable)
            script = self.script_crud.find_by_id(session, script_id)
            if not script:
                raise BusinessLogicError(f"Script not found: {script_id}")

        # 3. VALIDATION: Node Name
        name = node_data.get('name', '').strip()
        if not name:
            raise ValidationError("Node name is required")
        
        # Check if name contains only valid characters
        if not name.replace('_', '').replace('-', '').replace(' ', '').isalnum():
            raise ValidationError("Node name must contain only alphanumeric characters, hyphens, underscores, and spaces")
        
        # 4. VALIDATION: Node Name Uniqueness
        existing_node = self.node_crud.node_name_exists_in_workflow(session, name, node_data.get('workflow_id'))
        if existing_node:
            raise ValidationError(f"Node with name '{name}' already exists in workflow")

        # 5. OPERATION: Create Node
        node = self.node_crud.create_node(session, **node_data)

        # 6. RETURN: API Format
        return node.to_dict()

    def update(self, session: Session, node_id: str, node_data: Dict[str, Any]) -> Dict[str, Any]:
        """Node güncelleme"""
        # 1. VALIDATION: Node ID
        old_node = self.node_crud.find_by_id(session, node_id)
        if not old_node:
            raise BusinessLogicError(f"Node not found: {node_id}")

        # 2. VALIDATION: Workflow ID
        if 'workflow_id' in node_data and node_data['workflow_id'] != old_node.workflow_id:
            workflow = self.workflow_crud.find_by_id(session, node_data['workflow_id'])
            if not workflow:
                raise BusinessLogicError(f"Workflow not found: {node_data['workflow_id']}")

        # 3. VALIDATION: Script ID
        if 'script_id' in node_data and node_data['script_id']:
            script = self.script_crud.find_by_id(session, node_data['script_id'])
            if not script:
                raise BusinessLogicError(f"Script not found: {node_data['script_id']}")

        # 4. VALIDATION: Node Name
        if 'name' in node_data and node_data['name'] != old_node.name:
            name = node_data['name'].strip()
            if not name:
                raise ValidationError("Node name is required")
            
            # Check if name contains only valid characters
            if not name.replace('_', '').replace('-', '').replace(' ', '').isalnum():
                raise ValidationError("Node name must contain only alphanumeric characters, hyphens, underscores, and spaces")
            
            # Check name uniqueness
            workflow_id = node_data.get('workflow_id', old_node.workflow_id)
            existing_node = self.node_crud.node_name_exists_in_workflow(session, name, workflow_id)
            if existing_node:
                raise ValidationError(f"Node with name '{name}' already exists in workflow")
            
            # Update the name in node_data
            node_data['name'] = name

        # 5. OPERATION: Update Node
        updated_node = self.node_crud.update_node(session, node_id, **node_data)
        
        # 6. RETURN: API Format
        return updated_node.to_dict()

    def delete(self, session: Session, node_id: str, force: bool = False) -> Dict[str, Any]:
        """Node silme"""
        # 1. VALIDATION: Node ID
        node = self.node_crud.find_by_id(session, node_id)
        if not node:
            raise BusinessLogicError(f"Node not found: {node_id}")

        # 2. VALIDATION: Node Dependencies
        if not force:
            # Check incoming edges
            incoming_edges = self.edge_crud.filter(session, {'to_node_id': node_id})
            if incoming_edges:
                raise BusinessLogicError(f"Cannot delete node '{node.name}' - it has {len(incoming_edges)} incoming dependencies. Use force=True to override.")
            
            # Check outgoing edges
            outgoing_edges = self.edge_crud.filter(session, {'from_node_id': node_id})
            if outgoing_edges:
                raise BusinessLogicError(f"Cannot delete node '{node.name}' - it has {len(outgoing_edges)} outgoing dependencies. Use force=True to override.")

        # 3. OPERATION: Delete related edges first
        if force:
            # Delete incoming edges
            incoming_edges = self.edge_crud.filter(session, {'to_node_id': node_id})
            for edge in incoming_edges:
                # Edge silme işlemi - başarısız olsa bile devam et
                try:
                    self.edge_crud.delete_edge(session, edge.id)
                except Exception:
                    # Edge already deleted or other error, continue
                    continue
            
            # Delete outgoing edges
            outgoing_edges = self.edge_crud.filter(session, {'from_node_id': node_id})
            for edge in outgoing_edges:
                # Edge silme işlemi - başarısız olsa bile devam et
                try:
                    self.edge_crud.delete_edge(session, edge.id)
                except Exception:
                    # Edge already deleted or other error, continue
                    continue

        # 4. OPERATION: Delete Node
        deleted_node = self.node_crud.delete_node(session, node_id)

        # 5. RETURN: API Format
        return deleted_node.to_dict()

    def get(self, session: Session, node_id: str, include_details: bool = False) -> Dict[str, Any]:
        """Node detayını getir"""
        # 1. VALIDATION: Node ID
        node = self.node_crud.find_by_id(session, node_id)
        if not node:
            raise BusinessLogicError(f"Node not found: {node_id}")
        
        # 2. OPERATION: Get base node data
        node_dict = node.to_dict()
        
        # 3. OPERATION: Add enhanced details if requested
        if include_details:
            # Add workflow name
            workflow = self.workflow_crud.find_by_id(session, node.workflow_id)
            node_dict['workflow_name'] = workflow.name if workflow else None
            
            # Add script details (if exists)
            if node.script_id:
                script = self.script_crud.find_by_id(session, node.script_id)
                if script:
                    node_dict['script_name'] = script.name
                    node_dict['script_input_params'] = script.input_params
                    node_dict['script_output_params'] = script.output_params
                    node_dict['script_language'] = script.language.value if hasattr(script.language, 'value') else script.language
                    node_dict['script_test_status'] = script.test_status.value if hasattr(script.test_status, 'value') else script.test_status
                else:
                    node_dict['script_name'] = None
                    node_dict['script_input_params'] = None
                    node_dict['script_output_params'] = None
                    node_dict['script_language'] = None
                    node_dict['script_test_status'] = None
            else:
                node_dict['script_name'] = None
                node_dict['script_input_params'] = None
                node_dict['script_output_params'] = None
                node_dict['script_language'] = None
                node_dict['script_test_status'] = None
            
            # Add dependency counts
            node_dict['incoming_dependencies'] = self.edge_crud.count_dependencies(session, node_id)
            node_dict['outgoing_dependencies'] = self.edge_crud.count_dependants(session, node_id)
            
            # Add self-dependency check
            node_dict['has_self_dependency'] = self._has_self_dependency(session, node_id)
        
        # 4. RETURN: API Format
        return node_dict

    def search(self, session: Session, search_criteria: Dict[str, Any], skip: int = 0, limit: int = 100, order_by_field: str = None) -> Dict[str, Any]:
        """Node arama"""
        # 1. OPERATION: Search nodes
        nodes = self.node_crud.filter(session, search_criteria, skip=skip, limit=limit, order_by_field=order_by_field)
        
        # Get total count for pagination
        total_count = self.node_crud.count_filtered(session, search_criteria)
        
        # 2. RETURN: API Format
        return {
            'data': [node.to_dict() for node in nodes],
            'total_count': total_count,
            'skip': skip,
            'limit': limit,
            'has_more': (skip + limit) < total_count
        }

    def count(self, session: Session, workflow_id: Optional[str] = None) -> int:
        """Node sayısını getir"""
        if workflow_id:
            return self.node_crud.count_filtered(session, {'workflow_id': workflow_id})
        return self.node_crud.count(session)
    
    def exists(self, session: Session, node_id: str) -> bool:
        """Node var mı kontrolü"""
        return self.node_crud.exists(session, node_id)

    def _has_self_dependency(self, session: Session, node_id: str) -> bool:
        """
        Check if node has a direct self-dependency (edge from itself to itself)
        """
        try:
            edges = self.edge_crud.filter(session, {'from_node_id': node_id, 'to_node_id': node_id})
            return len(edges) > 0
        except Exception:
            return False

    def get_all(self, session: Session) -> List[Dict[str, Any]]:
        """Tüm node'ları getir"""
        nodes = self.node_crud.get_all(session)
        return [node.to_dict() for node in nodes]

    def get_by_workflow(self, session: Session, workflow_id: str) -> List[Dict[str, Any]]:
        """Belirli bir workflow'a ait node'ları getir"""
        # 1. VALIDATION: Workflow ID
        if not workflow_id:
            raise ValidationError("Workflow ID is required")
            
        workflow = self.workflow_crud.find_by_id(session, workflow_id)
        if not workflow:
            raise BusinessLogicError(f"Workflow not found: {workflow_id}")
        
        # 2. OPERATION: Get nodes by workflow
        nodes = self.node_crud.get_by_workflow(session, workflow_id)
        return [node.to_dict() for node in nodes]

    def get_by_script(self, session: Session, script_id: str) -> List[Dict[str, Any]]:
        """Belirli bir script'e ait node'ları getir"""
        # 1. VALIDATION: Script ID
        if not script_id:
            raise ValidationError("Script ID is required")
            
        script = self.script_crud.find_by_id(session, script_id)
        if not script:
            raise BusinessLogicError(f"Script not found: {script_id}")
        
        # 2. OPERATION: Get nodes by script
        nodes = self.node_crud.get_by_script(session, script_id)
        return [node.to_dict() for node in nodes]