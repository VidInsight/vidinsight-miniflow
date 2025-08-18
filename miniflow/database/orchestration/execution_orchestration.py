# orchestration/execution_orchestration.py
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, Union, List
from datetime import datetime, timezone

from .base_orchestration import BaseOrchestration
from ...exceptions import (
    ValidationError, 
    BusinessLogicError
)
from ..models import ExecutionStatus


class ExecutionOrchestrator(BaseOrchestration):
    """
    Execution orchestration operations for workflow execution management.
    
    Provides high-level operations for creating, monitoring, and managing
    workflow executions with task scheduling, dependency resolution, and
    result collection.
    """

    def __init__(self):
        """
        Initialize ExecutionOrchestrator.
        
        Args:
            None
            
        Returns:
            None
            
        Raises:
            None
        """
        super().__init__()

    def create(self, session: Session, workflow_id: str) -> Dict[str, Any]:
        """
        Create a new workflow execution with task scheduling and dependency setup.
        
        Args:
            session (Session): Database session for transaction management
            workflow_id (str): Unique identifier of workflow to execute
            
        Returns:
            Dict[str, Any]: Created execution data with task information
            
        Raises:
            BusinessLogicError: If workflow not found or has no nodes
            DatabaseError: If database operation fails
        """
        workflow = self.workflow_crud.find_by_id(session, workflow_id)
        if not workflow:
            raise BusinessLogicError(f"Workflow not found: {workflow_id}")
        
        # 2. VALIDATION: Get all nodes for this workflow
        nodes = self.node_crud.get_by_workflow(session, workflow_id)
        if not nodes:
            raise BusinessLogicError(f"Cannot create execution - no nodes found for workflow: {workflow_id}")
        
        # 3. OPERATION: Create execution record
        execution_payload = {
            'workflow_id': workflow_id,
            'pending_nodes': len(nodes),
            'executed_nodes': 0,
        }
        execution = self.execution_crud.create_execution(session, **execution_payload)
     
        # 4. OPERATION: Create execution inputs
        created_inputs = 0
        for node in nodes:
            # 4.1. OPERATION: Get node script info (if exists)
            script_path = None
            if node.script_id:
                script = self.script_crud.find_by_id(session, node.script_id)
                if script:
                    script_path = script.script_path
            
            # 4.2. OPERATION: Create execution input record
            execution_input_payload = {
                'workflow_id': workflow_id,
                'execution_id': execution.id,
                'node_id': node.id,
                'priority': workflow.priority,
                'dependency_count': self.edge_crud.count_filtered(session, {'to_node_id': node.id}),
                'node_name': node.name,
                'script_path': script_path,
                'node_params': node.params
            }
            self.execution_input_crud.create_execution_input(session, **execution_input_payload)
            created_inputs += 1

        # 5. RETURN: API Format
        return execution.to_dict()

    def cancel(self, session: Session, execution_id: str) -> Dict[str, Any]:
        """Execution iptal etme"""
        execution = self.execution_crud.find_by_id(session, execution_id)
        if not execution:
            raise BusinessLogicError(f"Execution not found: {execution_id}")
        
        # 2. VALIDATION: Check if execution can be cancelled
        if execution.status in [ExecutionStatus.COMPLETED, ExecutionStatus.FAILED, ExecutionStatus.CANCELLED]:
            raise BusinessLogicError(f"Cannot cancel execution with status: {execution.status.value}")
        
        # 3. OPERATION: Get Execution Inputs
        execution_inputs = self.execution_input_crud.get_by_execution(session, execution_id)
        if execution_inputs:
            for execution_input in execution_inputs:
                self.execution_input_crud.delete_execution_input(session, execution_input.id)

        # 4. OPERATION: Collect Execution Outputs
        execution_results = []

        execution_outputs = self.execution_output_crud.get_by_execution(session, execution_id)
        if execution_outputs:
            for execution_output in execution_outputs:
                execution_results.append(execution_output.results)
                self.execution_output_crud.delete_execution_output(session, execution_output.id)
        
        # 5. OPERATION: Set Execution Results for cancelled inputs
        for execution_input in execution_inputs:
            # Get node name from node relationship
            node = self.node_crud.find_by_id(session, execution_input.node_id)
            node_name = node.name if node else None
            
            execution_results.append({
                'node_id': execution_input.node_id,
                'node_name': node_name,
                'status': 'cancelled',
                'script_path': execution_input.script_path if hasattr(execution_input, 'script_path') else None,
                'node_params': execution_input.node_params if hasattr(execution_input, 'node_params') else None,
            })

        results = {
            'execution_id': execution_id,
            'execution_results': execution_results,
        }

        # 6. OPERATION: Update Execution
        execution_payload = {
            'status': ExecutionStatus.CANCELLED,
            'ended_at': datetime.now(timezone.utc),
            'results': results
        }
        updated_execution = self.execution_crud.update_execution(session, execution_id, **execution_payload)
        
        # 7. RETURN: API Format
        return updated_execution.to_dict()

    def search(self, session: Session, search_criteria: Dict[str, Any], skip: int = 0, limit: int = 100, order_by_field: str = None) -> Dict[str, Any]:
        """Execution arama"""
        # 1. OPERATION: Search executions
        executions = self.execution_crud.filter(session, search_criteria, skip=skip, limit=limit, order_by_field=order_by_field)
        
        # Get total count for pagination
        total_count = self.execution_crud.count_filtered(session, search_criteria)
        
        # 2. RETURN: API Format
        return {
            'data': [execution.to_dict() for execution in executions],
            'total_count': total_count,
            'skip': skip,
            'limit': limit,
            'has_more': (skip + limit) < total_count
        }
  
    def get_all(self, session: Session) -> List[Dict[str, Any]]:
        """Tüm execution'ları getir"""
        executions = self.execution_crud.get_all(session)
        return [execution.to_dict() for execution in executions]
        
    def get(self, session: Session, execution_id: str, include_details: bool = False) -> Dict[str, Any]:
        """Execution detayını getir"""
        # 1. VALIDATION: Execution ID
        execution = self.execution_crud.find_by_id(session, execution_id)
        if not execution:
            raise BusinessLogicError(f"Execution not found: {execution_id}")

        # 2. OPERATION: Get base execution data
        execution_dict = execution.to_dict()
        
        # 3. OPERATION: Add enhanced details if requested
        if include_details:
            # Add workflow name
            workflow = self.workflow_crud.find_by_id(session, execution.workflow_id)
            execution_dict['workflow_name'] = workflow.name if workflow else None
            
            # Add execution inputs and outputs count
            inputs = self.execution_input_crud.get_by_execution(session, execution_id)
            outputs = self.execution_output_crud.get_by_execution(session, execution_id)
            execution_dict['input_count'] = len(inputs) if inputs else 0
            execution_dict['output_count'] = len(outputs) if outputs else 0

        # 4. RETURN: API Format
        return execution_dict

    def get_results(self, session: Session, execution_id: str) -> Dict[str, Any]:
        """Execution sonuçlarını getir"""
        # 1. VALIDATION: Execution ID
        execution = self.execution_crud.find_by_id(session, execution_id)
        if not execution:
            raise BusinessLogicError(f"Execution not found: {execution_id}")
        
        # 2. OPERATION: Get execution results from execution record
        if hasattr(execution, 'results') and execution.results:
            return execution.results
        
        # 3. OPERATION: If no results in execution, collect from outputs
        execution_outputs = self.execution_output_crud.get_by_execution(session, execution_id)
        if not execution_outputs:
            raise BusinessLogicError(f"No execution results found for execution: {execution_id}")
        
        # 4. OPERATION: Compile results from outputs
        results = {
            'execution_id': execution_id,
            'execution_results': [output.results for output in execution_outputs if output.results]
        }
        
        # 5. RETURN: API Format
        return results

    def get_status(self, session: Session, execution_id: str) -> Dict[str, Any]:
        """Execution durumunu getir"""
        # 1. VALIDATION: Execution ID
        execution = self.execution_crud.find_by_id(session, execution_id)
        if not execution:
            raise BusinessLogicError(f"Execution not found: {execution_id}")

        # 2. RETURN: API Format with consistent structure
        return {
            'execution_id': execution_id,
            'status': execution.status,
            'started_at': execution.started_at,
            'ended_at': execution.ended_at,
            'pending_nodes': execution.pending_nodes,
            'executed_nodes': execution.executed_nodes
        }

    def count(self, session: Session) -> int:
        """Execution sayısını getir"""
        return self.execution_crud.count(session)
    
    def exists(self, session: Session, execution_id: str) -> bool:
        """Execution var mı kontrolü"""
        return self.execution_crud.exists(session, execution_id)

    def get_by_workflow(self, session: Session, workflow_id: str) -> List[Dict[str, Any]]:
        """Belirli bir workflow'a ait execution'ları getir"""
        # 1. VALIDATION: Workflow ID
        workflow = self.workflow_crud.find_by_id(session, workflow_id)
        if not workflow:
            raise BusinessLogicError(f"Workflow not found: {workflow_id}")
        
        # 2. OPERATION: Get executions by workflow
        executions = self.execution_crud.get_by_workflow(session, workflow_id)
        return [execution.to_dict() for execution in executions]

    def count_by_workflow(self, session: Session, workflow_id: str) -> int:
        """Belirli bir workflow'a ait execution sayısını getir"""
        # 1. VALIDATION: Workflow ID
        workflow = self.workflow_crud.find_by_id(session, workflow_id)
        if not workflow:
            raise BusinessLogicError(f"Workflow not found: {workflow_id}")
        
        # 2. OPERATION: Count executions by workflow
        return self.execution_crud.count_by_workflow(session, workflow_id)

    def get_running_executions(self, session: Session) -> List[Dict[str, Any]]:
        """Running durumundaki execution'ları getir"""
        executions = self.execution_crud.get_by_status(session, ExecutionStatus.RUNNING)
        return [execution.to_dict() for execution in executions]

    def get_pending_executions(self, session: Session) -> List[Dict[str, Any]]:
        """Pending durumundaki execution'ları getir"""
        executions = self.execution_crud.get_by_status(session, ExecutionStatus.PENDING)
        return [execution.to_dict() for execution in executions]

    def get_canceled_executions(self, session: Session) -> List[Dict[str, Any]]:
        """Cancelled durumundaki execution'ları getir"""
        executions = self.execution_crud.get_by_status(session, ExecutionStatus.CANCELLED)
        return [execution.to_dict() for execution in executions]

    def get_failed_executions(self, session: Session) -> List[Dict[str, Any]]:
        """Failed durumundaki execution'ları getir"""
        executions = self.execution_crud.get_by_status(session, ExecutionStatus.FAILED)
        return [execution.to_dict() for execution in executions]

    def get_completed_executions(self, session: Session) -> List[Dict[str, Any]]:
        """Completed durumundaki execution'ları getir"""
        executions = self.execution_crud.get_by_status(session, ExecutionStatus.COMPLETED)
        return [execution.to_dict() for execution in executions]

    def count_running_executions(self, session: Session) -> int:
        """Running execution sayısını getir"""
        return self.execution_crud.count_by_status(session, ExecutionStatus.RUNNING)

    def count_pending_executions(self, session: Session) -> int:
        """Pending execution sayısını getir"""
        return self.execution_crud.count_by_status(session, ExecutionStatus.PENDING)

    def count_canceled_executions(self, session: Session) -> int:
        """Cancelled execution sayısını getir"""
        return self.execution_crud.count_by_status(session, ExecutionStatus.CANCELLED)

    def count_failed_executions(self, session: Session) -> int:
        """Failed execution sayısını getir"""
        return self.execution_crud.count_by_status(session, ExecutionStatus.FAILED)

    def count_completed_executions(self, session: Session) -> int:
        """Completed execution sayısını getir"""
        return self.execution_crud.count_by_status(session, ExecutionStatus.COMPLETED)

    def get_running_executions_of_workflow(self, session: Session, workflow_id: str) -> List[Dict[str, Any]]:
        """Belirli bir workflow'un running execution'larını getir"""
        # 1. VALIDATION: Workflow ID
        workflow = self.workflow_crud.find_by_id(session, workflow_id)
        if not workflow:
            raise BusinessLogicError(f"Workflow not found: {workflow_id}")
        
        # 2. OPERATION: Get running executions by workflow
        executions = self.execution_crud.get_by_status_and_workflow(session, workflow_id, ExecutionStatus.RUNNING)
        return [execution.to_dict() for execution in executions]

    def get_pending_executions_of_workflow(self, session: Session, workflow_id: str) -> List[Dict[str, Any]]:
        """Belirli bir workflow'un pending execution'larını getir"""
        # 1. VALIDATION: Workflow ID
        workflow = self.workflow_crud.find_by_id(session, workflow_id)
        if not workflow:
            raise BusinessLogicError(f"Workflow not found: {workflow_id}")
        
        # 2. OPERATION: Get pending executions by workflow
        executions = self.execution_crud.get_by_status_and_workflow(session, workflow_id, ExecutionStatus.PENDING)
        return [execution.to_dict() for execution in executions]

    def get_completed_executions_of_workflow(self, session: Session, workflow_id: str) -> List[Dict[str, Any]]:
        """Belirli bir workflow'un completed execution'larını getir"""
        # 1. VALIDATION: Workflow ID
        workflow = self.workflow_crud.find_by_id(session, workflow_id)
        if not workflow:
            raise BusinessLogicError(f"Workflow not found: {workflow_id}")
        
        # 2. OPERATION: Get completed executions by workflow
        executions = self.execution_crud.get_by_status_and_workflow(session, workflow_id, ExecutionStatus.COMPLETED)
        return [execution.to_dict() for execution in executions]

    def get_failed_executions_of_workflow(self, session: Session, workflow_id: str) -> List[Dict[str, Any]]:
        """Belirli bir workflow'un failed execution'larını getir"""
        # 1. VALIDATION: Workflow ID
        if not workflow_id:
            raise ValidationError("Workflow ID is required")
            
        workflow = self.workflow_crud.find_by_id(session, workflow_id)
        if not workflow:
            raise BusinessLogicError(f"Workflow not found: {workflow_id}")
        
        # 2. OPERATION: Get failed executions by workflow
        executions = self.execution_crud.get_by_status_and_workflow(session, workflow_id, ExecutionStatus.FAILED)
        return [execution.to_dict() for execution in executions]

    def get_canceled_executions_of_workflow(self, session: Session, workflow_id: str) -> List[Dict[str, Any]]:
        """Belirli bir workflow'un cancelled execution'larını getir"""
        # 1. VALIDATION: Workflow ID
        if not workflow_id:
            raise ValidationError("Workflow ID is required")
            
        workflow = self.workflow_crud.find_by_id(session, workflow_id)
        if not workflow:
            raise BusinessLogicError(f"Workflow not found: {workflow_id}")
        
        # 2. OPERATION: Get cancelled executions by workflow
        executions = self.execution_crud.get_by_status_and_workflow(session, workflow_id, ExecutionStatus.CANCELLED)
        return [execution.to_dict() for execution in executions]

    def get_execution_statistics(self, session: Session, workflow_id: str = None) -> Dict[str, Any]:
        """Execution istatistiklerini getir"""
        # 1. VALIDATION: Workflow ID (if provided)
        if workflow_id:
            workflow = self.workflow_crud.find_by_id(session, workflow_id)
            if not workflow:
                raise BusinessLogicError(f"Workflow not found: {workflow_id}")
        
        # 2. OPERATION: Get statistics
        stats = self.execution_crud.get_execution_statistics(session, workflow_id)
        return {
            'workflow_id': workflow_id,
            'statistics': stats
        }

    def set_execution_status(self, session: Session, execution_id: str, status: ExecutionStatus) -> Dict[str, Any]:
        """Execution status'unu güncelle"""
        # 1. VALIDATION: Execution ID
        execution = self.execution_crud.find_by_id(session, execution_id)
        if not execution:
            raise BusinessLogicError(f"Execution not found: {execution_id}")
        
        # 2. VALIDATION: Status
        if not isinstance(status, ExecutionStatus):
            raise ValidationError("Invalid execution status")
        
        # 3. OPERATION: Set status
        updated_execution = self.execution_crud.set_execution_status(session, execution_id, status)
        return updated_execution.to_dict()

    def set_execution_steps(self, session: Session, execution_id: str, pending_nodes: int = None, executed_nodes: int = None) -> Dict[str, Any]:
        """Execution step counts'ları güncelle"""
        # 1. VALIDATION: Execution ID
        execution = self.execution_crud.find_by_id(session, execution_id)
        if not execution:
            raise BusinessLogicError(f"Execution not found: {execution_id}")
        
        # 2. VALIDATION: At least one parameter required
        if pending_nodes is None and executed_nodes is None:
            raise ValidationError("At least one step count must be provided")
        
        # 3. VALIDATION: Non-negative values
        if pending_nodes is not None and pending_nodes < 0:
            raise ValidationError("Pending nodes count cannot be negative")
        if executed_nodes is not None and executed_nodes < 0:
            raise ValidationError("Executed nodes count cannot be negative")
        
        # 4. OPERATION: Set step counts
        updated_execution = self.execution_crud.set_execution_steps(session, execution_id, pending_nodes, executed_nodes)
        return updated_execution.to_dict()

    def set_execution_results(self, session: Session, execution_id: str, results: Dict[str, Any]) -> Dict[str, Any]:
        """Execution results'ları güncelle"""
        # 1. VALIDATION: Execution ID
        execution = self.execution_crud.find_by_id(session, execution_id)
        if not execution:
            raise BusinessLogicError(f"Execution not found: {execution_id}")
        
        # 2. VALIDATION: Results
        if not results or not isinstance(results, dict):
            raise ValidationError("Results must be a non-empty dictionary")
        
        # 3. OPERATION: Set results
        updated_execution = self.execution_crud.set_execution_results(session, execution_id, results)
        return updated_execution.to_dict()

    def get_executions_by_date_range(self, session: Session, start_date: datetime, end_date: datetime, status: ExecutionStatus = None) -> List[Dict[str, Any]]:
        """Tarih aralığındaki execution'ları getir"""
        # 1. VALIDATION: Date range
        if not start_date or not end_date:
            raise ValidationError("Start date and end date are required")
        if start_date >= end_date:
            raise ValidationError("Start date must be before end date")
        
        # 2. OPERATION: Get executions by date range
        executions = self.execution_crud.get_executions_by_date_range(session, start_date, end_date, status)
        return [execution.to_dict() for execution in executions]

    def get_long_running_executions(self, session: Session, timeout_hours: int = 24) -> List[Dict[str, Any]]:
        """Uzun süre çalışan execution'ları getir"""
        # 1. VALIDATION: Timeout hours
        if timeout_hours <= 0:
            raise ValidationError("Timeout hours must be positive")
        
        # 2. OPERATION: Get long running executions
        executions = self.execution_crud.get_long_running_executions(session, timeout_hours)
        return [execution.to_dict() for execution in executions]

    def get_execution_inputs(self, session: Session, execution_id: str) -> List[Dict[str, Any]]:
        """Execution'a ait execution input'ları getir"""
        # 1. VALIDATION: Execution ID
        execution = self.execution_crud.find_by_id(session, execution_id)
        if not execution:
            raise BusinessLogicError(f"Execution not found: {execution_id}")
        
        # 2. OPERATION: Get execution inputs
        execution_inputs = self.execution_input_crud.get_by_execution(session, execution_id)
        return [execution_input.to_dict() for execution_input in execution_inputs]

    def get_execution_outputs(self, session: Session, execution_id: str) -> List[Dict[str, Any]]:
        """Execution'a ait execution output'ları getir"""
        # 1. VALIDATION: Execution ID
        execution = self.execution_crud.find_by_id(session, execution_id)
        if not execution:
            raise BusinessLogicError(f"Execution not found: {execution_id}")
        
        # 2. OPERATION: Get execution outputs
        execution_outputs = self.execution_output_crud.get_by_execution(session, execution_id)
        return [execution_output.to_dict() for execution_output in execution_outputs]