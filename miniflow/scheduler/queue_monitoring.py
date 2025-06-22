import time
import threading
import os
import json

from .. import database
from . import context_manager
from ..utils.logger import logger, log_performance
from concurrent.futures import ThreadPoolExecutor
from ..database.functions.bulk_operations import bulk_get_nodes, bulk_resolve_contexts


class QueueMonitor:
    """
    Amaç: Execution queue'yu izler ve hazır taskları işler
    """

    def __init__(self, db_path, polling_interval=5, manager=None, batch_size=20):
        """
        Amaç: Queue monitor'u başlatır
        Döner: Yok (constructor)
        """
        self.db_path = db_path
        self.polling_interval = polling_interval
        self.running = False
        self.thread = None
        current_dir = os.path.dirname(os.path.abspath(__file__))  # miniflow/scheduler
        miniflow_dir = os.path.dirname(current_dir)  # miniflow
        project_root = os.path.dirname(miniflow_dir)  # vi-miniflow (proje kök)
        self.scripts_dir = os.path.join(project_root, 'scripts')
        logger.debug(f"QueueMonitor scripts_dir: {self.scripts_dir}")

        self.manager = manager
        
        # Batch processing settings
        self.batch_size = batch_size
        self.enable_batch_processing = True  # Batch processing açık/kapalı
        logger.info(f"QueueMonitor initialized - batch_processing: {self.enable_batch_processing}, batch_size: {self.batch_size}")
        
        # Thread pool for parallel payload preparation
        self.payload_thread_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="PayloadPrep")

    def start(self):
        """
        Amaç: Monitoring'i başlatır
        Döner: Başarı durumu (True/False)
        """
        if self.running:
            return False

        # Database bağlantı kontrolü
        connection_result = database.check_database_connection(self.db_path)
        if not connection_result.success:
            return False

        self.running = True
        self.thread = threading.Thread(target=self.execution_loop, daemon=True)
        self.thread.start()
        logger.info("QueueMonitor started")
        return True

    def stop(self):
        """
        Amaç: Monitoring'i durdurur
        Döner: Yok
        """
        if not self.running:
            return

        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
        
        # Shutdown thread pool
        if hasattr(self, 'payload_thread_pool'):
            self.payload_thread_pool.shutdown(wait=True)
        
        logger.info("QueueMonitor stopped")

    def is_running(self):
        """
        Amaç: Servis durumunu kontrol eder
        Döner: Çalışma durumu (True/False)
        """
        return self.running and self.thread and self.thread.is_alive()

    def get_ready_tasks(self, limit=None):
        """
        Amaç: Tüm active execution'lar için hazır olan taskları alır
        Döner: Ready task listesi
        """
        # Batch processing için daha büyük limit kullan
        if limit is None:
            limit = self.batch_size * 2 if self.enable_batch_processing else 10
            
        all_ready_tasks = []

        try:
            # Tüm active execution'ları al
            executions_result = database.list_executions(self.db_path)
            if not executions_result.success:
                return []

            active_executions = [
                exec_data for exec_data in executions_result.data
                if exec_data.get('status') in ['running', 'pending']
            ]

            # Her active execution için ready task'ları al
            for execution in active_executions:
                execution_id = execution['id']

                ready_result = database.get_ready_tasks_for_execution(
                    db_path=self.db_path,
                    execution_id=execution_id,
                    limit=limit
                )

                if ready_result.success:
                    ready_tasks = ready_result.data.get('ready_tasks', [])
                    all_ready_tasks.extend(ready_tasks)

            # Limit uygula
            if limit and len(all_ready_tasks) > limit:
                all_ready_tasks = all_ready_tasks[:limit]

            logger.debug(f"Ready tasks found: {len(all_ready_tasks)}")
            return all_ready_tasks

        except Exception as e:
            logger.error(f"get_ready_tasks failed: {e}")
            return []

    def reorder_queue(self):
        """
        Amaç: Queue'yu yeniden düzenler (database function kullanır)
        Döner: Güncellenen task sayısı
        """
        result = database.reorder_execution_queue(self.db_path)

        if result.success:
            #print(f"[QueueMonitor] Queue reorder: {result.data.get('ready_count', 0)} task ready oldu.")
            return result.data.get('ready_count', 0)
        return 0

    @log_performance("execution_loop_cycle")
    def execution_loop(self):
        """
        Amaç: Ana monitoring döngüsü (Performance optimized batch processing)
        Döner: Yok (sonsuz döngü)
        """
        logger.info(f"QueueMonitor execution_loop started - batch_processing: {self.enable_batch_processing}")
        while self.running:
            try:
                # Queue'yu düzenle
                ready_count = self.reorder_queue()
                if ready_count > 0:
                    logger.debug(f"Queue reorder: {ready_count} tasks ready")

                # Ready taskları al
                ready_tasks = self.get_ready_tasks()
                
                if not ready_tasks:
                    time.sleep(self.polling_interval)
                    continue

                logger.info(f"Processing {len(ready_tasks)} ready tasks (batch_mode: {self.enable_batch_processing})")

                # TRUE Batch processing veya single processing
                if self.enable_batch_processing and len(ready_tasks) >= 2:
                    # TRUE Batch olarak işle (performance optimized)
                    logger.info(f"TRUE BATCH processing: {len(ready_tasks)} tasks")
                    self.process_tasks_true_batch(ready_tasks)
                else:
                    # Tek tek işle
                    logger.info(f"SINGLE processing: {len(ready_tasks)} tasks")
                    for task in ready_tasks:
                        if not self.running:
                            break

                        logger.debug(f"Processing single task: {task['id']}")
                        # Task'ı running olarak işaretle
                        database.mark_task_as_running(self.db_path, task['id'])

                        # Task'ı işle
                        self.process_task(task)

                # Polling interval bekle
                time.sleep(self.polling_interval)

            except Exception as e:
                logger.error(f"execution_loop error: {e}")
                time.sleep(1)

    def process_task(self, task):
        """
        Amaç: Tek bir task'ı işler
        Döner: İşlem başarı durumu (True/False)
        """
        #print(f"[QueueMonitor] process_task çağrıldı: {task}")
        try:
            task_id = task['id']
            node_id = task['node_id']
            execution_id = task['execution_id']

            # Node bilgilerini al
            node_result = database.get_node(self.db_path, node_id)
            if not node_result.success:
                #print(f"[QueueMonitor] Node alınamadı: {node_id}")
                return False

            node_info = node_result.data

            # Context oluştur (updated context manager ile execution_results query)
            params_dict = database.safe_json_loads(node_info.get('params', '{}'))
            #print("--------------------------------")
            #print(f"[QueueMonitor] Raw params: {params_dict}")
            
            # Handle double-encoded JSON
            if isinstance(params_dict, str):
                try:
                    params_dict = json.loads(params_dict)
                except json.JSONDecodeError as e:
                    #print(f"[QueueMonitor] Failed to parse params JSON: {e}")
                    return False
            
            """print(f"[QueueMonitor] Parsed params: {params_dict}")
            for key, value in params_dict.items():
                print(f"[QueueMonitor] {key}: {value}")
                print(f"[QueueMonitor] {type(key)}: {type(value)}")
            print("--------------------------------")"""

            processed_context = context_manager.create_context_for_task(
                params_dict, execution_id, self.db_path
            )

            # Task payload hazırla
            task_payload = {
                "execution_id": execution_id,
                "workflow_id": node_info['workflow_id'],
                "node_id": node_id,
                "script_path": os.path.join(self.scripts_dir, node_info.get('script', '')),
                "context": processed_context,
                "node_name": node_info['name'],
                "node_type": node_info['type']
            }

            #print(f"[QueueMonitor] Task payload input queue'ya gönderiliyor: {task_payload}")
            # Task'ı input queue'ya gönder
            send_success = self.send_to_input_queue(task_payload)

            if send_success:
                # Sadece başarılı gönderimden sonra sil
                delete_result = database.delete_task(self.db_path, task_id)
                #print(f"[QueueMonitor] Task input queue'ya gönderildi ve silindi: {task_id}")
                return delete_result.success
            else:
                #print(f"[QueueMonitor] Task input queue'ya gönderilemedi: {task_id}")
                return False

        except Exception as e:
            #print(f"[QueueMonitor] process_task hata: {e}")
            return False

    def send_to_input_queue(self, task_payload):
        """
        Amaç: Task'ı input queue'ya gönderir
        Döner: Başarı durumu (True/False)
        
        Bu implementasyon test amaçlı simulated execution yapar.
        Gerçek sistemde burası execution engine'e gönderecek.
        """
        try:
            #print(f"[QueueMonitor] send_to_input_queue çağrıldı: {task_payload}")
            self.manager.put_item(task_payload)
            #print(f"[QueueMonitor] put_item başarılı.")
            return True

        except Exception as e:
            #print(f"[QueueMonitor] send_to_input_queue hata: {e}")
            return False

    def process_tasks_batch(self, tasks):
        """
        Amaç: Birden fazla task'ı batch olarak işler
        Döner: İşlenen task sayısı
        """
        if not tasks:
            return 0
            
        batch_size = min(len(tasks), self.batch_size)
        current_batch = tasks[:batch_size]
        
        print(f"[QueueMonitor] Batch processing başlıyor: {len(current_batch)} task")
        
        try:
            # 1. Tüm task'ları running olarak işaretle (batch)
            task_ids = [task['id'] for task in current_batch]
            batch_success = self.batch_mark_tasks_as_running(task_ids)
            
            if not batch_success:
                print("[QueueMonitor] Batch mark failed, fallback to single processing")
                # Fallback: tek tek işle
                for task in current_batch:
                    database.mark_task_as_running(self.db_path, task['id'])
            
            # 2. Task payload'larını hazırla
            batch_payloads = []
            for task in current_batch:
                try:
                    payload = self.prepare_task_payload(task)
                    if payload:
                        batch_payloads.append(payload)
                except Exception as e:
                    print(f"[QueueMonitor] Payload hazırlama hatası: {e}")
                    continue
            
            # 3. Batch olarak engine'e gönder
            if batch_payloads:
                success_count = self.send_batch_to_input_queue(batch_payloads)
                print(f"[QueueMonitor] Batch tamamlandı: {success_count}/{len(batch_payloads)} task başarılı")
                return success_count
            
            return 0
            
        except Exception as e:
            print(f"[QueueMonitor] Batch processing hata: {e}")
            # Fallback: tek tek işle
            success_count = 0
            for task in current_batch:
                try:
                    database.mark_task_as_running(self.db_path, task['id'])
                    if self.process_task(task):
                        success_count += 1
                except:
                    continue
            return success_count
    
    def prepare_task_payload(self, task):
        """
        Amaç: Task için payload hazırlar (batch'ten çıkarıldı)
        Döner: Task payload dictionary'si
        """
        try:
            task_id = task['id']
            node_id = task['node_id']
            execution_id = task['execution_id']

            # Node bilgilerini al
            node_result = database.get_node(self.db_path, node_id)
            if not node_result.success:
                print(f"[QueueMonitor] Node alınamadı: {node_id}")
                return None

            node_info = node_result.data

            # Context oluştur
            params_dict = database.safe_json_loads(node_info.get('params', '{}'))
            
            # Handle double-encoded JSON
            if isinstance(params_dict, str):
                try:
                    params_dict = json.loads(params_dict)
                except json.JSONDecodeError as e:
                    print(f"[QueueMonitor] Failed to parse params JSON: {e}")
                    return None

            processed_context = context_manager.create_context_for_task(
                params_dict, execution_id, self.db_path
            )

            # Task payload oluştur
            task_payload = {
                "task_id": task_id,
                "execution_id": execution_id,
                "workflow_id": node_info['workflow_id'],
                "node_id": node_id,
                "script_path": os.path.join(self.scripts_dir, node_info.get('script', '')),
                "context": processed_context,
                "node_name": node_info['name'],
                "node_type": node_info['type']
            }
            
            return task_payload
            
        except Exception as e:
            print(f"[QueueMonitor] prepare_task_payload hata: {e}")
            return None
    
    def batch_mark_tasks_as_running(self, task_ids):
        """
        Amaç: Birden fazla task'ı running olarak işaretler
        Döner: Başarı durumu (True/False)
        """
        try:
            # Database batch operation kullan
            return database.batch_mark_tasks_as_running(self.db_path, task_ids)
        except Exception as e:
            print(f"[QueueMonitor] batch_mark_tasks_as_running hata: {e}")
            return False
    
    def send_batch_to_input_queue(self, batch_payloads):
        """
        Amaç: Birden fazla task payload'ını parallelism engine'e gönderir
        Döner: Başarılı gönderilen task sayısı
        """
        try:
            # Manager'da bulk method varsa kullan
            if hasattr(self.manager, 'put_items_bulk'):
                success = self.manager.put_items_bulk(batch_payloads)
                if success:
                    print(f"[QueueMonitor] Batch input queue'ya gönderildi: {len(batch_payloads)} task")
                    # Başarılı task'ları sil
                    for payload in batch_payloads:
                        try:
                            database.delete_task(self.db_path, payload.get('task_id'))
                        except:
                            pass
                    return len(batch_payloads)
                else:
                    print(f"[QueueMonitor] Batch input queue'ya gönderilemedi")
                    return 0
            else:
                # Fallback: tek tek gönder ama hızlı
                success_count = 0
                for payload in batch_payloads:
                    if self.manager.put_item(payload):
                        success_count += 1
                        # Başarılı task'ı sil
                        try:
                            database.delete_task(self.db_path, payload.get('task_id'))
                        except:
                            pass
                print(f"[QueueMonitor] Batch fallback: {success_count}/{len(batch_payloads)} task gönderildi")
                return success_count
                
        except Exception as e:
            print(f"[QueueMonitor] send_batch_to_input_queue hata: {e}")
            return 0

    @log_performance("true_batch_processing")
    def process_tasks_true_batch(self, tasks):
        """
        TRUE Batch Processing Implementation
        
        This method replaces the fake batch processing with real parallel processing:
        - Bulk database operations (1 query instead of N queries)
        - Parallel payload preparation (ThreadPoolExecutor)
        - True bulk queue operations
        - Bulk task deletion
        
        Expected performance: 10-20x faster than fake batch
        """
        if not tasks:
            return 0
            
        batch_size = min(len(tasks), self.batch_size)
        current_batch = tasks[:batch_size]
        
        logger.info(f"TRUE BATCH processing: {len(current_batch)} tasks")
        
        try:
            # Step 1: Bulk database marking (already implemented and working)
            task_ids = [task['id'] for task in current_batch]
            batch_success = self.batch_mark_tasks_as_running(task_ids)
            
            if not batch_success:
                logger.warning("Bulk mark failed, falling back to individual processing")
                return self._fallback_individual_processing(current_batch)
            
            # Step 2: Bulk node data fetch (NEW - replaces N individual queries)
            node_ids = [task['node_id'] for task in current_batch]
            nodes_result = bulk_get_nodes(self.db_path, node_ids)
            
            if not nodes_result.success:
                logger.error(f"Bulk node fetch failed: {nodes_result.error}")
                return self._fallback_individual_processing(current_batch)
            
            nodes_dict = nodes_result.data
            logger.debug(f"Bulk fetched {len(nodes_dict)} nodes")
            
            # Step 3: Bulk context resolution (NEW - replaces N individual context resolutions)
            tasks_with_params = []
            for task in current_batch:
                node_info = nodes_dict.get(task['node_id'])
                if node_info:
                    params_dict = database.safe_json_loads(node_info.get('params', '{}'))
                    if isinstance(params_dict, str):
                        try:
                            params_dict = json.loads(params_dict)
                        except json.JSONDecodeError:
                            params_dict = {}
                    tasks_with_params.append((task, params_dict))
            
            # Get execution_id from first task (all tasks in batch should have same execution_id)
            execution_id = current_batch[0]['execution_id'] if current_batch else None
            
            if execution_id and tasks_with_params:
                contexts_result = bulk_resolve_contexts(self.db_path, execution_id, tasks_with_params)
                if contexts_result.success:
                    resolved_contexts = contexts_result.data
                    logger.debug(f"Bulk resolved {len(resolved_contexts)} contexts")
                else:
                    logger.warning(f"Bulk context resolution failed: {contexts_result.error}")
                    resolved_contexts = [params for _, params in tasks_with_params]
            else:
                resolved_contexts = [params for _, params in tasks_with_params]
            
            # Step 4: Parallel payload preparation (NEW - uses ThreadPoolExecutor)
            batch_payloads = self._prepare_payloads_parallel(current_batch, nodes_dict, resolved_contexts)
            
            # Step 5: True bulk queue send (already optimized)
            if batch_payloads:
                success = self.manager.put_items_bulk(batch_payloads)
                if success:
                    # Step 6: Bulk task deletion (already implemented)
                    delete_result = database.batch_delete_tasks(self.db_path, task_ids)
                    if delete_result.success:
                        logger.info(f"TRUE BATCH completed: {len(batch_payloads)} tasks successfully processed")
                        return len(batch_payloads)
                    else:
                        logger.warning(f"Bulk delete failed: {delete_result.error}")
                        # Tasks were sent but not deleted - still count as success
                        return len(batch_payloads)
                else:
                    logger.error("Bulk queue send failed")
                    return 0
            
            return 0
            
        except Exception as e:
            logger.error(f"TRUE BATCH processing failed: {e}")
            return self._fallback_individual_processing(current_batch)
    
    def _prepare_payloads_parallel(self, tasks, nodes_dict, resolved_contexts):
        """
        Prepare task payloads in parallel using ThreadPoolExecutor
        
        This replaces the sequential payload preparation with parallel processing
        """
        batch_payloads = []
        
        # Create payload preparation tasks
        def prepare_single_payload_optimized(task, context):
            try:
                node_info = nodes_dict.get(task['node_id'])
                if not node_info:
                    logger.error(f"Node not found for task {task['id']}")
                    return None
                
                # Build payload
                task_payload = {
                    "task_id": task['id'],
                    "execution_id": task['execution_id'],
                    "workflow_id": node_info['workflow_id'],
                    "node_id": task['node_id'],
                    "script_path": os.path.join(self.scripts_dir, node_info.get('script', '')),
                    "context": context,
                    "node_name": node_info['name'],
                    "node_type": node_info['type']
                }
                
                return task_payload
                
            except Exception as e:
                logger.error(f"Payload preparation failed for task {task['id']}: {e}")
                return None
        
        # Submit all tasks to thread pool
        with ThreadPoolExecutor(max_workers=min(4, len(tasks))) as executor:
            futures = []
            for i, task in enumerate(tasks):
                context = resolved_contexts[i] if i < len(resolved_contexts) else {}
                future = executor.submit(prepare_single_payload_optimized, task, context)
                futures.append(future)
            
            # Collect results
            for future in futures:
                try:
                    payload = future.result(timeout=5)
                    if payload:
                        batch_payloads.append(payload)
                except Exception as e:
                    logger.error(f"Future failed: {e}")
        
        logger.debug(f"Parallel payload preparation: {len(batch_payloads)}/{len(tasks)} successful")
        return batch_payloads
    
    def _fallback_individual_processing(self, tasks):
        """
        Fallback to individual processing when batch fails
        """
        logger.info(f"Falling back to individual processing for {len(tasks)} tasks")
        success_count = 0
        for task in tasks:
            try:
                database.mark_task_as_running(self.db_path, task['id'])
                if self.process_task(task):
                    success_count += 1
            except Exception as e:
                logger.error(f"Individual task processing failed: {e}")
                continue
        return success_count