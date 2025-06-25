"""
Workflow Trigger Module

Bu modül workflow tetikleme işlemlerini yönetir.
Şu anda workflow_orchestration.py fonksiyonlarını kullanarak temel tetikleme sağlar.

Mevcut özellikler:
- Manuel workflow tetikleme (execution records oluşturur)
- Workflow execution başlatma
- Task queue'ya görev ekleme

Gelecek özellikler:
- Zamanlı tetikleme (cron-like)
- Event-driven tetikleme
- API tetikleme
"""

from typing import Dict, Any, Optional
from ..database.functions.workflow_orchestration import trigger_workflow_execution

from ..database.schema import Execution, ExecutionQueue
from ..database.config import DatabaseConnection

def clean_previous_executions(db_path: str, workflow_id: str):
    """
    Belirtilen workflow'a ait tamamlanmamış (completed olmayan) execution ve taskları temizler.
    """
    with DatabaseConnection(db_path) as session:
        # Tamamlanmamış executionları al (status 'completed' olmayanlar)
        unfinished_executions = session.query(Execution).filter(
            Execution.workflow_id == workflow_id,
            Execution.status != 'completed'
        ).all()

        for exec_obj in unfinished_executions:
            # Bu execution'a ait taskları sil
            session.query(ExecutionQueue).filter(
                ExecutionQueue.execution_id == exec_obj.id
            ).delete(synchronize_session=False)

            # İstersen, execution'a ait ExecutionResult kayıtlarını da silebilirsin
            # session.query(ExecutionResult).filter(
            #     ExecutionResult.execution_id == exec_obj.id
            # ).delete(synchronize_session=False)

            # Execution kaydını sil
            session.delete(exec_obj)

        session.commit()

class WorkflowTrigger:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def trigger_workflow_manually(self, workflow_id: str, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        try:
            clean_previous_executions(self.db_path, workflow_id)

            # Initial node ID'leri bul
            from ..database.schema import Node, Edge
            from ..database.config import DatabaseConnection
            

            with DatabaseConnection(self.db_path) as session:
                all_nodes = session.query(Node.id).filter_by(workflow_id=workflow_id).all()
                to_nodes = session.query(Edge.to_node_id).filter_by(workflow_id=workflow_id).distinct().all()

                all_node_ids = {n[0] for n in all_nodes}
                to_node_ids = {e[0] for e in to_nodes}
                initial_node_ids = list(all_node_ids - to_node_ids)

            if not initial_node_ids:
                return {
                    'success': False,
                    'error': 'Hiçbir başlangıç (initial) node bulunamadı.',
                    'workflow_id': workflow_id,
                    'method': 'manual'
                }

            result = trigger_workflow_execution(self.db_path, workflow_id, initial_node_ids)

            if result.success:
                return {
                    'success': True,
                    'execution_id': result.data.get('execution_id'),
                    'workflow_id': workflow_id,
                    'created_tasks': result.data.get('created_tasks', 0),
                    'ready_tasks': result.data.get('ready_tasks', 0),
                    'trigger_timestamp': result.data.get('trigger_timestamp'),
                    'method': 'manual',
                    'parameters': parameters,
                    'message': 'Workflow başarıyla tetiklendi.'
                }
            else:
                return {
                    'success': False,
                    'error': result.error,
                    'workflow_id': workflow_id,
                    'method': 'manual'
                }

        except Exception as e:
            return {
                'success': False,
                'error': f"Manual trigger failed: {str(e)}",
                'workflow_id': workflow_id,
                'method': 'manual'
            }


    def get_execution_status(self, execution_id: str) -> Dict[str, Any]:
        try:
            from ..database.functions.workflow_orchestration import get_execution_status_summary

            result = get_execution_status_summary(self.db_path, execution_id)

            if result.success:
                return {
                    'success': True,
                    'execution_id': execution_id,
                    'execution_data': result.data.get('execution'),
                    'task_counts': result.data.get('task_counts', {}),
                    'result_counts': result.data.get('result_counts', {}),
                    'total_tasks': result.data.get('total_tasks', 0),
                    'total_results': result.data.get('total_results', 0),
                    'summary_timestamp': result.data.get('summary_timestamp')
                }
            else:
                return {
                    'success': False,
                    'error': result.error,
                    'execution_id': execution_id
                }

        except Exception as e:
            return {
                'success': False,
                'error': f"Status check failed: {str(e)}",
                'execution_id': execution_id
            }

    def get_ready_tasks(self, execution_id: str, limit: int = 10) -> Dict[str, Any]:
        try:
            from ..database.functions.workflow_orchestration import get_ready_tasks_for_execution

            result = get_ready_tasks_for_execution(self.db_path, execution_id, limit)

            if result.success:
                return {
                    'success': True,
                    'execution_id': execution_id,
                    'ready_tasks': result.data.get('ready_tasks', []),
                    'ready_count': result.data.get('ready_count', 0),
                    'total_ready': result.data.get('total_ready', 0),
                    'limit_applied': limit
                }
            else:
                return {
                    'success': False,
                    'error': result.error,
                    'execution_id': execution_id
                }

        except Exception as e:
            return {
                'success': False,
                'error': f"Ready tasks fetch failed: {str(e)}",
                'execution_id': execution_id
            }

    def validate_workflow_exists(self, workflow_id: str) -> Dict[str, Any]:
        try:
            from ..database import get_workflow

            result = get_workflow(self.db_path, workflow_id)

            if result.success and result.data:
                return {
                    'success': True,
                    'workflow_id': workflow_id,
                    'workflow_exists': True,
                    'workflow_name': result.data.get('name', ''),
                    'workflow_description': result.data.get('description', '')
                }
            else:
                return {
                    'success': False,
                    'workflow_id': workflow_id,
                    'workflow_exists': False,
                    'error': 'Workflow not found'
                }

        except Exception as e:
            return {
                'success': False,
                'workflow_id': workflow_id,
                'workflow_exists': False,
                'error': f"Validation failed: {str(e)}"
            }

    def schedule_workflow(self, workflow_id: str, schedule: str, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return {
            'success': False,
            'error': 'Scheduling functionality not implemented yet',
            'note': 'Future feature for cron-like workflow scheduling',
            'workflow_id': workflow_id,
            'schedule': schedule
        }

    def setup_event_trigger(self, workflow_id: str, event_config: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'success': False,
            'error': 'Event triggering functionality not implemented yet',
            'note': 'Future feature for event-based workflow triggering',
            'workflow_id': workflow_id,
            'event_config': event_config
        }


def create_workflow_trigger(db_path: str) -> WorkflowTrigger:
    return WorkflowTrigger(db_path)


def trigger_workflow_manually(db_path: str, workflow_id: str, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    trigger = WorkflowTrigger(db_path)
    return trigger.trigger_workflow_manually(workflow_id, parameters)


def get_workflow_execution_status(db_path: str, execution_id: str) -> Dict[str, Any]:
    trigger = WorkflowTrigger(db_path)
    return trigger.get_execution_status(execution_id)


def get_workflow_ready_tasks(db_path: str, execution_id: str, limit: int = 10) -> Dict[str, Any]:
    trigger = WorkflowTrigger(db_path)
    return trigger.get_ready_tasks(execution_id, limit)
