# orchestration/scheduler_orchestration.py
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, Union, List
from datetime import datetime, timezone

from .base_orchestration import BaseOrchestration
from ...exceptions import ValidationError, BusinessLogicError, CRUDException, DatabaseError
from ..models import ExecutionOutputStatus


class SchedulerOrchestrator(BaseOrchestration):
    """Scheduler operasyonları için orchestrator"""

    def __init__(self):
        super().__init__()

    def get_ready_tasks(self, session: Session, limit: int = 10) -> List[Dict[str, Any]]:
        """Execution input tablosundan hazır taskları getir"""
        try:
            ready_tasks = self.execution_input_crud.get_ready_tasks(session, limit=limit)
            return [self._create_task_payload(task) for task in ready_tasks]
        except CRUDException as e:
            raise DatabaseError(f"Failed to get ready tasks: {str(e)}")

    def delete_completed_tasks(self, session: Session, task_ids: List[str]) -> int:
        """Execution input tablosundan tamamlanan taskları sil"""
        if not task_ids:
            return 0
        
        deleted_count = 0
        failed_deletions = []
        
        for task_id in task_ids:
            try:
                self.execution_input_crud.delete_execution_input(session, task_id)
                deleted_count += 1
            except CRUDException as e:
                failed_deletions.append(f"Task {task_id}: {str(e)}")
                continue
        
        if failed_deletions:
            # Log failed deletions but don't fail the entire operation
            print(f"Warning: Failed to delete some tasks: {failed_deletions}")
        
        return deleted_count

    def create_task_payload(self, task: Any) -> Dict[str, Any]:
        """Task objesi için execution payload oluştur"""
        if task is None:
            raise ValidationError("Task cannot be None")
        
        # Task zaten dict formatında geliyorsa direkt döndür
        if isinstance(task, dict):
            required_fields = ['id', 'execution_id', 'node_id', 'workflow_id']
            if not all(field in task for field in required_fields):
                raise ValidationError(f"Task dict missing required fields: {required_fields}")
            return task
        
        # ExecutionInput objesi ise dict'e çevir
        return self._create_task_payload(task)
    
    def process_execution_result(self, session: Session, result: Dict[str, Any]) -> bool:
        """Execution result'ı işle ve execution output oluştur"""
        if not isinstance(result, dict):
            raise ValidationError("Result must be a dictionary")
        
        # Required fields validation
        execution_id = result.get('execution_id')
        node_id = result.get('node_id')
        status = result.get('status')
        
        if not all([execution_id, node_id, status]):
            raise ValidationError("Missing required fields: execution_id, node_id, status")
        
        if status not in ['success', 'failure']:
            raise ValidationError("Status must be 'success' or 'failure'")
        
        try:
            # 1. Execution output oluştur
            self._create_execution_output(session, result)
            
            # 2. Başarılı ise dependency count'ları güncelle  
            if status == 'success':
                self._update_dependencies(session, node_id, execution_id)
            
            # 3. Tamamlanan task'ı sil
            self._delete_completed_task(session, execution_id, node_id)
            
            return True
            
        except ValidationError:
            # Validation errors'ı yukarı fırlat
            raise
        except CRUDException as e:
            raise DatabaseError(f"Failed to process execution result: {str(e)}")

    def _create_execution_output(self, session: Session, result: Dict[str, Any]) -> None:
        """Private: Execution output oluştur"""
        execution_id = result['execution_id']
        node_id = result['node_id']
        status = result['status']
        result_data = result.get('result_data', {})
        
        # Status'u enum'a çevir
        output_status = (
            ExecutionOutputStatus.SUCCESS if status == 'success' 
            else ExecutionOutputStatus.FAILURE
        )
        
        output_payload = {
            'execution_id': execution_id,
            'node_id': node_id,
            'status': output_status,
            'result_data': result_data,
            'started_at': result.get('started_at', datetime.now(timezone.utc)),
            'ended_at': result.get('ended_at', datetime.now(timezone.utc))
        }
        
        self.execution_output_crud.create_execution_output(session, **output_payload)

    def _update_dependencies(self, session: Session, node_id: str, execution_id: str) -> None:
        """Private: Dependency count'ları güncelle"""
        # Bu node'a bağlı olan diğer node'ların dependency count'larını azalt
        edges = self.edge_crud.filter(session, {'from_node_id': node_id})
        
        for edge in edges:
            # Execution input'ta bu edge'in to_node'ı için dependency count'ı azalt
            try:
                execution_input = self.execution_input_crud.get_by_execution_and_node(
                    session, execution_id, edge.to_node_id
                )
                if execution_input and execution_input.dependency_count > 0:
                    execution_input.dependency_count -= 1
                    session.flush()
            except CRUDException:
                # Execution input not found, skip
                continue

    def _delete_completed_task(self, session: Session, execution_id: str, node_id: str) -> None:
        """Private: Tamamlanan task'ı sil"""
        try:
            execution_input = self.execution_input_crud.get_by_execution_and_node(
                session, execution_id, node_id
            )
            if execution_input:
                self.execution_input_crud.delete_execution_input(session, execution_input.id)
        except CRUDException:
            # Already deleted, skip
            pass

    def collect_final_results(self, session: Session, execution_id: str) -> Dict[str, Any]:
        """Execution'ın final result'larını topla"""
        try:
            # Execution'ı bul
            execution = self.execution_crud.find_by_id(session, execution_id)
            if not execution:
                raise BusinessLogicError(f"Execution not found: {execution_id}")
            
            # Tüm execution output'larını topla
            outputs = self.execution_output_crud.get_by_execution(session, execution_id)
            
            # Result'ları organize et
            results = {}
            for output in outputs:
                results[output.node_id] = {
                    'status': str(output.status),
                    'result_data': output.result_data,
                    'started_at': output.started_at,
                    'ended_at': output.ended_at
                }
            
            return {
                'execution_id': execution_id,
                'workflow_id': execution.workflow_id,
                'status': str(execution.status),
                'results': results,
                'total_nodes': len(results)
            }
            
        except CRUDException as e:
            raise DatabaseError(f"Failed to collect final results: {str(e)}")

    def check_if_last_node(self, session: Session, node_id: str, execution_id: str) -> bool:
        """Bu node execution'daki son node mu kontrol et"""
        try:
            # Execution'ı bul
            execution = self.execution_crud.find_by_id(session, execution_id)
            if not execution:
                raise BusinessLogicError(f"Execution not found: {execution_id}")
            
            # Bu workflow'daki tüm node'ları bul
            workflow_nodes = self.node_crud.get_by_workflow(session, execution.workflow_id)
            
            # Bu node'dan çıkan edge'leri bul
            outgoing_edges = self.edge_crud.filter(session, {'from_node_id': node_id})
            
            # Eğer bu node'dan çıkan edge yoksa, bu son node'dur
            return len(outgoing_edges) == 0
            
        except CRUDException as e:
            raise DatabaseError(f"Failed to check if last node: {str(e)}")

    def _create_task_payload(self, task) -> Dict[str, Any]:
        """Private: Task objesi için payload oluştur"""
        return {
            'id': task.id,
            'execution_id': task.execution_id,
            'node_id': task.node_id,
            'workflow_id': task.workflow_id,
            'input_data': task.node_params,  
            'dependency_count': task.dependency_count,
            'created_at': task.created_at
        }