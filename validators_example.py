# validators/workflow_validator.py - ÖRNEK
from typing import List, Dict, Any
from pydantic import BaseModel, ValidationError
from ...exceptions import ValidationError as MiniflowValidationError

class WorkflowValidator:
    """Workflow validation kuralları"""
    
    @staticmethod
    def validate_workflow_name(name: str) -> bool:
        """Workflow name validation"""
        if not name or not name.strip():
            raise MiniflowValidationError("Workflow name cannot be empty")
        
        if len(name) > 100:
            raise MiniflowValidationError("Workflow name too long (max 100 chars)")
        
        # Special characters check
        invalid_chars = ['<', '>', ':', '"', '|', '?', '*', '\\', '/']
        for char in invalid_chars:
            if char in name:
                raise MiniflowValidationError(f"Workflow name cannot contain '{char}'")
        
        return True
    
    @staticmethod
    def validate_workflow_structure(nodes: List[Dict], edges: List[Dict]) -> bool:
        """Workflow structure validation"""
        
        # 1. Node validation
        if not nodes:
            raise MiniflowValidationError("Workflow must have at least one node")
        
        node_names = set()
        for node in nodes:
            if not node.get("name"):
                raise MiniflowValidationError("All nodes must have a name")
            
            if node["name"] in node_names:
                raise MiniflowValidationError(f"Duplicate node name: {node['name']}")
            
            node_names.add(node["name"])
        
        # 2. Edge validation
        for edge in edges:
            source = edge.get("source")
            target = edge.get("target")
            
            if not source or not target:
                raise MiniflowValidationError("All edges must have source and target")
            
            if source not in node_names:
                raise MiniflowValidationError(f"Edge source '{source}' not found in nodes")
            
            if target not in node_names:
                raise MiniflowValidationError(f"Edge target '{target}' not found in nodes")
            
            if source == target:
                raise MiniflowValidationError(f"Edge cannot connect node to itself: {source}")
        
        # 3. Connectivity check (at least one path from start to end)
        if edges:
            if not WorkflowValidator._has_valid_path(nodes, edges):
                raise MiniflowValidationError("Workflow must have valid connectivity")
        
        return True
    
    @staticmethod
    def validate_node_configuration(node: Dict) -> bool:
        """Individual node configuration validation"""
        
        required_fields = ["name", "script_id", "params"]
        for field in required_fields:
            if field not in node:
                raise MiniflowValidationError(f"Node missing required field: {field}")
        
        # Script ID validation
        script_id = node.get("script_id")
        if script_id and not script_id.startswith("SC-"):
            raise MiniflowValidationError("Invalid script ID format")
        
        # Timeout validation
        timeout = node.get("timeout_seconds", 300)
        if timeout < 1 or timeout > 3600:
            raise MiniflowValidationError("Timeout must be between 1 and 3600 seconds")
        
        # Retry validation
        max_retries = node.get("max_retries", 3)
        if max_retries < 0 or max_retries > 10:
            raise MiniflowValidationError("Max retries must be between 0 and 10")
        
        return True
    
    @staticmethod
    def validate_edge_configuration(edge: Dict) -> bool:
        """Individual edge configuration validation"""
        
        required_fields = ["source", "target"]
        for field in required_fields:
            if field not in edge:
                raise MiniflowValidationError(f"Edge missing required field: {field}")
        
        # Condition validation
        condition = edge.get("condition")
        if condition:
            valid_conditions = ["always", "success", "failure", "timeout"]
            if condition not in valid_conditions:
                raise MiniflowValidationError(f"Invalid condition: {condition}. Must be one of {valid_conditions}")
        
        return True
    
    @staticmethod
    def _has_valid_path(nodes: List[Dict], edges: List[Dict]) -> bool:
        """Check if workflow has valid connectivity"""
        # Simple connectivity check - can be enhanced with graph algorithms
        if not edges:
            return len(nodes) == 1  # Single node workflow
        
        # Build adjacency list
        graph = {}
        for edge in edges:
            source = edge["source"]
            target = edge["target"]
            
            if source not in graph:
                graph[source] = []
            graph[source].append(target)
        
        # Check if all nodes are reachable
        reachable = set()
        for node in nodes:
            node_name = node["name"]
            if node_name in graph:
                reachable.add(node_name)
                reachable.update(graph[node_name])
        
        return len(reachable) == len(nodes)

# validators/script_validator.py - ÖRNEK
class ScriptValidator:
    """Script validation kuralları"""
    
    @staticmethod
    def validate_script_name(name: str) -> bool:
        """Script name validation"""
        if not name or not name.strip():
            raise MiniflowValidationError("Script name cannot be empty")
        
        if len(name) > 50:
            raise MiniflowValidationError("Script name too long (max 50 chars)")
        
        # File name validation
        invalid_chars = ['<', '>', ':', '"', '|', '?', '*', '\\', '/']
        for char in invalid_chars:
            if char in name:
                raise MiniflowValidationError(f"Script name cannot contain '{char}'")
        
        return True
    
    @staticmethod
    def validate_script_content(content: str) -> bool:
        """Script content validation"""
        if not content or not content.strip():
            raise MiniflowValidationError("Script content cannot be empty")
        
        if len(content) > 100000:  # 100KB limit
            raise MiniflowValidationError("Script content too large (max 100KB)")
        
        # Basic Python syntax check
        try:
            compile(content, '<string>', 'exec')
        except SyntaxError as e:
            raise MiniflowValidationError(f"Invalid Python syntax: {str(e)}")
        
        return True
    
    @staticmethod
    def validate_script_parameters(input_params: Dict, output_params: Dict) -> bool:
        """Script parameter validation"""
        
        # Input parameters validation
        for param_name, param_config in input_params.items():
            if not param_name or not param_name.strip():
                raise MiniflowValidationError("Parameter name cannot be empty")
            
            if not isinstance(param_config, dict):
                raise MiniflowValidationError(f"Parameter config must be dict: {param_name}")
            
            required_fields = ["type", "description"]
            for field in required_fields:
                if field not in param_config:
                    raise MiniflowValidationError(f"Parameter '{param_name}' missing '{field}'")
        
        # Output parameters validation
        for param_name, param_config in output_params.items():
            if not param_name or not param_name.strip():
                raise MiniflowValidationError("Parameter name cannot be empty")
            
            if not isinstance(param_config, dict):
                raise MiniflowValidationError(f"Parameter config must be dict: {param_name}")
        
        return True

# validators/execution_validator.py - ÖRNEK
class ExecutionValidator:
    """Execution validation kuralları"""
    
    @staticmethod
    def validate_execution_start(workflow_id: str) -> bool:
        """Execution start validation"""
        if not workflow_id or not workflow_id.strip():
            raise MiniflowValidationError("Workflow ID required")
        
        if not workflow_id.startswith("WF-"):
            raise MiniflowValidationError("Invalid workflow ID format")
        
        return True
    
    @staticmethod
    def validate_execution_cancel(execution_id: str) -> bool:
        """Execution cancel validation"""
        if not execution_id or not execution_id.strip():
            raise MiniflowValidationError("Execution ID required")
        
        if not execution_id.startswith("EX-"):
            raise MiniflowValidationError("Invalid execution ID format")
        
        return True
