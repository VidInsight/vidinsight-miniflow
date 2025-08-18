# orchestration/scheduler_orchestration.py
from sqlalchemy.orm import Session
from typing import Dict, Any, List
from datetime import datetime, timezone

from .base_orchestration import BaseOrchestration
from ...exceptions import ValidationError, BusinessLogicError, CRUDException, DatabaseError
from ..models import ExecutionOutputStatus
from ..utils.scheduler_utils import categorize_variables


class SchedulerOrchestrator(BaseOrchestration):
    """
    Scheduler orchestration operations for task execution management.
    
    Provides high-level operations for task scheduling, execution monitoring,
    result processing, and dependency management for the workflow execution engine.
    """

    def __init__(self):
        """
        Initialize SchedulerOrchestrator.
        """
        super().__init__()

    def get_ready_tasks(self, session: Session, limit: int = 10, resolve_params: bool = True) -> List[Dict[str, Any]]:
        """
        Get ready tasks from execution input table for processing.
        
        Args:
            session (Session): Database session for transaction management
            limit (int): Maximum number of tasks to retrieve (default: 10)
            resolve_params (bool): Whether to resolve dynamic parameters (default: True)
            
        Returns:
            List[Dict[str, Any]]: List of ready task payloads for execution
            
        Raises:
            DatabaseError: If database operation fails or task retrieval fails
        """
        try:
            ready_tasks = self.execution_input_crud.get_ready_tasks(session, limit=limit)
            task_payloads = [self.create_task_payload(task) for task in ready_tasks]
            
            # Parametreleri resolve et
            if resolve_params:
                resolved_payloads = []
                for payload in task_payloads:
                    try:
                        resolved_payload = self.resolve_task_parameters(session, payload)
                        resolved_payloads.append(resolved_payload)
                    except Exception as e:
                        # Resolve edilemeyen task'lar için warning log ve original payload'ı kullan
                        print(f"Warning: Failed to resolve parameters for task {payload.get('id')}: {e}")
                        resolved_payloads.append(payload)
                return resolved_payloads
            
            return task_payloads
            
        except CRUDException as e:
            raise DatabaseError(f"Failed to get ready tasks: {str(e)}")



    def create_task_payload(self, task: Any) -> Dict[str, Any]:
        """
        Create execution payload for a task object.
        
        Args:
            task: Task object containing execution input data
            
        Returns:
            Dict[str, Any]: Task payload ready for execution
            
        Raises:
            ValidationError: If task data is invalid or incomplete
        """
        if task is None:
            raise ValidationError("Task cannot be None")
        
        # Task zaten dict formatında geliyorsa direkt döndür
        if isinstance(task, dict):
            required_fields = ['id', 'execution_id', 'node_id', 'workflow_id']
            if not all(field in task for field in required_fields):
                raise ValidationError(f"Task dict missing required fields: {required_fields}")
            return task
        
        # ExecutionInput objesi ise dict'e çevir
        return {
            'id': task.id,
            'execution_id': task.execution_id,
            'node_id': task.node_id,
            'workflow_id': task.workflow_id,
            'input_data': task.node_params,  
            'dependency_count': task.dependency_count,
            'created_at': task.created_at
        }
    
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
            
            # 3. Task silme işlemi cascade ile otomatik yapılacak
            # Execution silindiğinde ExecutionInput'lar da silinecek
            
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
            # Execution'ı bul (workflow_id için)
            execution = self.execution_crud.find_by_id(session, execution_id)
            if not execution:
                raise BusinessLogicError(f"Execution not found: {execution_id}")
            
            # Bu node'dan çıkan edge'leri bul
            outgoing_edges = self.edge_crud.filter(session, {'from_node_id': node_id})
            
            # Eğer bu node'dan çıkan edge yoksa, bu son node'dur
            return len(outgoing_edges) == 0
            
        except CRUDException as e:
            raise DatabaseError(f"Failed to check if last node: {str(e)}")

    def _resolve_environment_variable(self, session: Session, record_id: str = None, record_name: str = None) -> Any:
        """Private: Environment variable değerini çözümle"""
        
        if record_id is not None:
            record = self.envar_crud.find_by_id(session, record_id)
            return record.value
        elif record_name is not None:
            record = self.envar_crud.find_by_name(session, record_name)
            return record.value
        else:
            raise ValidationError("Record ID or name is required")

    def _resolve_node_output_value(self, session: Session, node_id: str, output_key: str) -> Any:
        """Private: Node output değerini çözümle"""
        record = self.execution_output_crud.find_by_id(session, node_id)
        value = record.result_data.get('data').get(output_key)
        return value

    def resolve_single_parameter(self, session: Session, param_value: Any, 
                                execution_id: str = None, workflow_id: str = None) -> Any:
        """
        Tek bir parametre değerini çözümle
        
        Args:
            session (Session): Database session
            param_value (Any): Çözümlenecek parametre değeri
            execution_id (str, optional): Execution ID
            workflow_id (str, optional): Workflow ID
            
        Returns:
            Any: Çözümlenmiş değer
        """
        try:
            # Tek değerli sözlük ile context çözümle
            context = self.resolve_parameter_context(
                session, 
                {"temp": param_value}, 
                execution_id=execution_id, 
                workflow_id=workflow_id
            )
            return context.get("temp", param_value)
            
        except Exception:
            # Çözümlenemezse orijinal değeri döndür
            return param_value

    def resolve_parameter_context(self, session: Session, params: Dict[str, Any], 
                                execution_id: str = None, workflow_id: str = None) -> Dict[str, Any]:
        """
        Parametre sözlüğünden execution context oluştur
        
        Args:
            session (Session): Database session
            params (Dict[str, Any]): Parametre sözlüğü (dynamic, environment, static değerler içerebilir)
            execution_id (str, optional): Execution ID (dynamic values için gerekli olabilir)
            workflow_id (str, optional): Workflow ID (node name bazlı dynamic values için gerekli)
            
        Returns:
            Dict[str, Any]: Değişken adı - değer eşleştirmesi
            
        Raises:
            ValidationError: Parametre geçersizse
            DatabaseError: Database işlemi başarısızsa
        """
        if not isinstance(params, dict):
            raise ValidationError("Parameters must be a dictionary")
        
        try:
            # Parametreleri kategorize et
            categorized = categorize_variables(params)
            
            # Sonuç sözlüğü
            context = {}
            
            # 1. Static değişkenleri direkt ekle
            for static_var in categorized['static_variables']:
                var_name = static_var['variable_name']
                value = static_var['value']
                context[var_name] = value
            
            # 2. Environment değişkenlerini resolve et
            for env_var in categorized['environment_variables']:
                var_name = env_var['variable_name']
                env_variable = env_var['env_variable']
                try:
                    value = self._resolve_environment_variable(session, record_name=env_variable)
                    context[var_name] = value
                except Exception as e:
                    # Environment variable bulunamazsa None yap
                    context[var_name] = None
                    print(f"Warning: Environment variable '{env_variable}' not found: {e}")
            
            # 3. Dynamic ID bazlı değişkenleri resolve et
            for dynamic_id_var in categorized['dynamic_variable_by_id']:
                var_name = dynamic_id_var['variable_name']
                node_id = dynamic_id_var['dynamic_id']
                target_variable = dynamic_id_var['target_variable']
                try:
                    value = self._resolve_node_output_value(session, node_id, target_variable)
                    context[var_name] = value
                except Exception as e:
                    # Node output bulunamazsa None yap
                    context[var_name] = None
                    print(f"Warning: Dynamic ID '{node_id}.{target_variable}' not found: {e}")
            
            # 4. Dynamic Name bazlı değişkenleri resolve et
            for dynamic_name_var in categorized['dynamic_variable_by_name']:
                var_name = dynamic_name_var['variable_name']
                node_name = dynamic_name_var['node_name']
                target_variable = dynamic_name_var['target_variable']
                try:
                    # Node name'i node ID'ye çevir (node_crud üzerinden)
                    # Workflow ID gerekirse kullan
                    if workflow_id:
                        node = self.node_crud.get_by_name_and_workflow(session, node_name, workflow_id)
                    else:
                        node = self.node_crud.find_by_name(session, node_name)
                    
                    if node:
                        value = self._resolve_node_output_value(session, node.id, target_variable)
                        context[var_name] = value
                    else:
                        context[var_name] = None
                        print(f"Warning: Node '{node_name}' not found")
                except Exception as e:
                    # Node output bulunamazsa None yap
                    context[var_name] = None
                    print(f"Warning: Dynamic name '{node_name}.{target_variable}' not found: {e}")
            
            return context
            
        except ValidationError:
            # Validation errors'ı yukarı fırlat
            raise
        except CRUDException as e:
            raise DatabaseError(f"Failed to create execution context: {str(e)}")
        except Exception as e:
            raise DatabaseError(f"Unexpected error creating execution context: {str(e)}")

    def resolve_task_parameters(self, session: Session, task_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Task payload'ındaki parametreleri resolve et
        
        Args:
            session (Session): Database session
            task_payload (Dict[str, Any]): Task payload with input_data
            
        Returns:
            Dict[str, Any]: Resolved parametrelerle güncellenmiş task payload
        """
        if not isinstance(task_payload, dict):
            raise ValidationError("Task payload must be a dictionary")
        
        # input_data'yı al
        input_data = task_payload.get('input_data', {})
        
        if not input_data:
            return task_payload
        
        try:
            # Context için gerekli ID'leri al
            execution_id = task_payload.get('execution_id')
            workflow_id = task_payload.get('workflow_id')
            
            # Parametreleri resolve et
            resolved_context = self.resolve_parameter_context(
                session, 
                input_data, 
                execution_id=execution_id, 
                workflow_id=workflow_id
            )
            
            # Task payload'ı güncelle
            updated_payload = task_payload.copy()
            updated_payload['input_data'] = resolved_context
            updated_payload['resolved_at'] = datetime.now(timezone.utc)
            
            return updated_payload
            
        except Exception as e:
            raise DatabaseError(f"Failed to resolve task parameters: {str(e)}")

    def cleanup_old_executions(self, session: Session, days_old: int = 30) -> int:
        """
        Eski execution'ları temizle
        
        Args:
            session (Session): Database session
            days_old (int): Kaç günden eski execution'lar silinecek (default: 30)
            
        Returns:
            int: Silinen execution sayısı
        """
        try:
            from datetime import timedelta
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_old)
            
            # Eski execution'ları bul
            old_executions = self.execution_crud.filter(session, {
                'created_at__lt': cutoff_date,
                'status__in': ['completed', 'failed', 'cancelled']
            })
            
            deleted_count = 0
            for execution in old_executions:
                try:
                    # Cascade ile tüm bağımlı kayıtlar silinecek
                    self.execution_crud.delete_execution(session, execution.id)
                    deleted_count += 1
                except Exception as e:
                    print(f"Warning: Failed to delete execution {execution.id}: {e}")
                    continue
            
            return deleted_count
            
        except Exception as e:
            raise DatabaseError(f"Failed to cleanup old executions: {str(e)}")

    def cleanup_audit_logs(self, session: Session, days_old: int = 90) -> int:
        """
        Eski audit log'ları temizle
        
        Args:
            session (Session): Database session
            days_old (int): Kaç günden eski log'lar silinecek (default: 90)
            
        Returns:
            int: Silinen log sayısı
        """
        try:
            return self.audit_log_crud.cleanup_old_logs(session, days_old)
        except Exception as e:
            raise DatabaseError(f"Failed to cleanup audit logs: {str(e)}")

    def get_system_statistics(self, session: Session) -> Dict[str, Any]:
        """
        Sistem istatistiklerini getir
        
        Returns:
            Dict[str, Any]: Sistem istatistikleri
        """
        try:
            stats = {}
            
            # Execution istatistikleri
            stats['executions'] = {
                'total': self.execution_crud.count_all(session),
                'pending': self.execution_crud.count_filtered(session, {'status': 'pending'}),
                'running': self.execution_crud.count_filtered(session, {'status': 'running'}),
                'completed': self.execution_crud.count_filtered(session, {'status': 'completed'}),
                'failed': self.execution_crud.count_filtered(session, {'status': 'failed'})
            }
            
            # Workflow istatistikleri
            stats['workflows'] = {
                'total': self.workflow_crud.count_all(session),
                'active': self.workflow_crud.count_filtered(session, {'status': 'active'}),
                'draft': self.workflow_crud.count_filtered(session, {'status': 'draft'})
            }
            
            # Audit log istatistikleri
            stats['audit_logs'] = self.audit_log_crud.get_log_statistics(session)
            
            return stats
            
        except Exception as e:
            raise DatabaseError(f"Failed to get system statistics: {str(e)}")