from concurrent.futures import as_completed
import logging

# Miniflow Database Module
from miniflow.database_manager import DatabaseEngine
from miniflow.database_manager import DatabaseOrchestration
from .base_monitor import BaseMonitor

logger = logging.getLogger(__name__)


class MiniflowInputMonitor(BaseMonitor):
    def __init__(self, database_engine: DatabaseEngine, database_orchestration: DatabaseOrchestration, execution_engine,
                 polling_interval=0.1, batch_size=50, worker_threads=4):
        # Initialize base monitor with InputWorker prefix
        super().__init__(
            database_engine=database_engine,
            database_orchestration=database_orchestration,
            execution_engine=execution_engine,
            polling_interval=polling_interval,
            batch_size=batch_size,
            worker_threads=worker_threads,
            thread_name_prefix="InputWorker"
        )
        
    def _process_cycle(self):
        """Process one cycle of input monitoring"""
        # ------------------------------------------------------------
        # 1. Görevleri kontrol eder ve hazır olanları işleme alır 
        # Hazır görevler -> dependency_count = 0 olan görevler -> priority'ye göre sıralanır
        # ------------------------------------------------------------
        ready_tasks = None
        with self.database_engine.get_session_context() as session:
            ready_tasks = self.database_orchestration.get_ready_tasks(session, self.batch_size)

        # ------------------------------------------------------------
        # 2. Görevleri işleme alır ve Execution Engine'e gönderir
        # ------------------------------------------------------------
        if ready_tasks:
            logger.debug(f"{len(ready_tasks)} hazır görev bulundu")
            self._send_tasks(ready_tasks)

    def _send_tasks(self, tasks):
        """Send tasks to execution engine"""
        # Check if manager is available
        if not self.execution_engine:
            logger.error("Görev gönderimi için Execution Engine mevcut değil")
            raise ValueError("Input Monitor için Execution Engine mecvut değil")
        
        logger.info(f"{len(tasks)} hazır görev işleniyor")

        # ------------------------------------------------------------
        # 1. Her görev (task) için context oluştur
        # Thread Pool üzeirnde multithread olarak gerçekleştir
        # ------------------------------------------------------------
        payload_futures = []                                                                  
        for task in tasks:
            future = self.worker_pool.submit(self._create_task_payload_with_session, task)
            payload_futures.append(future)

        # ------------------------------------------------------------
        # 2. Threadlerden gelen çıktıları topla
        # Future yapısı ile işlem gerçekleştiriliyor
        # ------------------------------------------------------------

        prepared_payloads = []
        task_ids = []
        
        for future in as_completed(payload_futures, timeout=10):
            try:
                payload = future.result()
                if payload:
                    prepared_payloads.append(payload)
                    task_ids.append(payload['id'])
                    logger.debug(f"Payload hazırlandı - task: {payload['node_name']}")
            except Exception as e:
                logger.error(f"Payload oluşturma hatası: {e}")

        logger.info(f"{len(prepared_payloads)} payload hazırlandı ({len(tasks)} task'dan)")
        
        # ------------------------------------------------------------
        # 3. Görevleri Execution Engine'a işleme gönder
        #Execution Engine üzerinde gerçekleştilriyor
        # ------------------------------------------------------------

        if prepared_payloads:
            # ------------------------------------------------------------
            # 3.1 Görevleri Execution Engine'a bulk olrak gönder
            # ------------------------------------------------------------
            logger.info(f"{len(prepared_payloads)} task parallelism engine'e gönderiliyor")
            success = self.execution_engine.put_items_bulk(prepared_payloads)                                # Hazır işlemleri motor'a gönder
            logger.debug(f"Bulk gönderim sonucu: {success}")
            
            if success:
                # ------------------------------------------------------------
                # 3.2 Göreve gönderilen görevleri tablodan sil
                # ------------------------------------------------------------
                with self.database_engine.get_session_context() as session:
                    removed_count = self.database_orchestration.remove_completed_tasks(session, task_ids)
                    logger.debug(f"{removed_count} tasks removed from queue")
            else:
                logger.error("Task'lar parallelism engine'e gönderilemedi")
        else:
            logger.warning(f"{len(tasks)} task'dan hiç payload hazırlanamadı")