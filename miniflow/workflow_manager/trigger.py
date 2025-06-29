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


class WorkflowTrigger:
    """
    Amaç: Workflow tetikleme işlemlerini yönetir
    
    Bu class workflow_orchestration.py fonksiyonlarını kullanarak
    workflow execution'larını başlatır ve execution records oluşturur.
    """
    
    def __init__(self, db_path: str):
        """
        Amaç: WorkflowTrigger'ı başlatır
        Döner: Yok (constructor)
        """
        self.db_path = db_path
    
    def trigger_workflow_manually(self, workflow_id: str, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Amaç: Workflow'u manuel olarak tetikler ve execution records oluşturur
        Döner: Tetikleme sonucu ve execution bilgileri
        
        Bu fonksiyon workflow_orchestration.trigger_workflow_execution() kullanır:
        - Execution record oluşturur
        - Tüm node'ları task queue'ya ekler
        - Dependency count'ları hesaplar
        - Ready task'ları belirler
        """
        try:
            # workflow_orchestration.py'den trigger_workflow_execution kullan
            result = trigger_workflow_execution(self.db_path, workflow_id)
            
            if result.success:
                return {
                    'success': True,
                    'execution_id': result.data.get('execution_id'),
                    'workflow_id': workflow_id,
                    'created_tasks': result.data.get('created_tasks', 0),
                    'ready_tasks': result.data.get('ready_tasks', 0),
                    'trigger_timestamp': result.data.get('trigger_timestamp'),
                    'method': 'manual',
                    'parameters': parameters,  # Future kullanım için sakla
                    'message': 'Workflow successfully triggered and execution records created'
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
        """
        Amaç: Tetiklenen workflow'un execution durumunu kontrol eder
        Döner: Execution durum bilgileri
        
        workflow_orchestration.get_execution_status_summary() kullanır
        """
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
        """
        Amaç: Tetiklenen workflow'da çalıştırılmaya hazır task'ları getirir
        Döner: Ready task listesi
        
        workflow_orchestration.get_ready_tasks_for_execution() kullanır
        """
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
        """
        Amaç: Workflow'un tetiklenmeden önce mevcut olup olmadığını kontrol eder
        Döner: Validation sonucu
        """
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
    
    # Placeholder methods for future implementation
    def schedule_workflow(self, workflow_id: str, schedule: str, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Amaç: Workflow'u zamanlı olarak tetiklemek için schedule eder (gelecek implementasyon)
        Döner: Schedule sonucu
        """
        return {
            'success': False,
            'error': 'Scheduling functionality not implemented yet',
            'note': 'Future feature for cron-like workflow scheduling',
            'workflow_id': workflow_id,
            'schedule': schedule
        }
    
    def setup_event_trigger(self, workflow_id: str, event_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Amaç: Event-driven workflow tetikleme setup'ı (gelecek implementasyon)
        Döner: Setup sonucu
        """
        return {
            'success': False,
            'error': 'Event triggering functionality not implemented yet',
            'note': 'Future feature for event-based workflow triggering',
            'workflow_id': workflow_id,
            'event_config': event_config
        }


# Factory functions
def create_workflow_trigger(db_path: str) -> WorkflowTrigger:
    """
    Amaç: WorkflowTrigger factory function
    Döner: WorkflowTrigger instance
    """
    return WorkflowTrigger(db_path)


def trigger_workflow_manually(db_path: str, workflow_id: str, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Amaç: Tek seferlik manuel workflow tetikleme (convenience function)
    Döner: Tetikleme sonucu
    
    Bu fonksiyon workflow_orchestration.trigger_workflow_execution() wrapper'ı
    """
    trigger = WorkflowTrigger(db_path)
    return trigger.trigger_workflow_manually(workflow_id, parameters)


def get_workflow_execution_status(db_path: str, execution_id: str) -> Dict[str, Any]:
    """
    Amaç: Convenience function - execution status kontrolü
    Döner: Execution durum bilgileri
    """
    trigger = WorkflowTrigger(db_path)
    return trigger.get_execution_status(execution_id)


def get_workflow_ready_tasks(db_path: str, execution_id: str, limit: int = 10) -> Dict[str, Any]:
    """
    Amaç: Convenience function - ready task'ları getir
    Döner: Ready task listesi
    """
    trigger = WorkflowTrigger(db_path)
    return trigger.get_ready_tasks(execution_id, limit)
