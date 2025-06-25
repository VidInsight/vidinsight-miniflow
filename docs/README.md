# Miniflow Kod Tabanı Dökümantasyonu

Bu döküman, Miniflow projesinin ana modüllerinin ve klasörlerinin yapısını ve işlevlerini özetler.

---

## 1. `database` Modülü

Veritabanı işlemlerinin tamamı bu modülde toplanır. SQLite tabanlıdır ve aşağıdaki ana bileşenleri içerir:

- **core.py**: Temel SQL işlemleri, tablo oluşturma/silme, bağlantı yönetimi.
- **config.py**: Veritabanı bağlantı ayarları ve context manager.
- **schema.py**: Tüm tablo ve index şemaları.
- **exceptions.py**: Hata yönetimi ve Result objesi.
- **utils.py**: UUID, JSON işlemleri, yardımcı fonksiyonlar.
- **functions/**: Tablolara özel CRUD ve iş mantığı fonksiyonları (ör: nodes_table.py, edges_table.py, triggers_table.py, workflow_orchestration.py).

**Öne Çıkan Sınıf/Fonksiyonlar:**
- `DatabaseConfig`, `DatabaseConnection`, `Result`
- `execute_sql_query`, `fetch_one`, `fetch_all`, `init_database`, `create_all_tables`, `drop_all_tables`

---

## 2. `scheduler` Modülü

Workflow task'larının otomatik olarak işlenmesini ve sonuçların izlenmesini sağlar. Ana bileşenler:

- **queue_monitoring.py**: QueueMonitor sınıfı ile execution queue'yu izler, hazır task'ları işler ve input queue'ya gönderir.
- **result_monitoring.py**: ResultMonitor sınıfı ile tamamlanan task sonuçlarını alır ve workflow orchestration'a besler.
- **scheduler.py**: WorkflowScheduler ile QueueMonitor ve ResultMonitor'u koordine eder, health check ve auto-recovery içerir.
- **context_manager.py**: Task parametrelerinde placeholder/bağımlılık çözümleme ve context oluşturma.

**Öne Çıkan Sınıf/Fonksiyonlar:**
- `QueueMonitor`, `ResultMonitor`, `WorkflowScheduler`
- `get_ready_tasks`, `process_task`, `send_to_input_queue`, `execution_loop`

---

## 3. `workflow_manager` Modülü

Workflow'ların yüklenmesi, doğrulanması ve tetiklenmesi için kullanılır. Ana bileşenler:

- **loader.py**: WorkflowLoader ile JSON workflow dosyalarını okur, validate eder ve veritabanına yükler. (Kritik: node_name.variable → node_id.variable mapping)
- **trigger.py**: WorkflowTrigger ile workflow tetikleme, execution başlatma ve durum sorgulama.
- **utils/workflow_parser.py**: JSON parsing, metadata extraction, node/trigger extraction ve yapısal validation.

**Öne Çıkan Sınıf/Fonksiyonlar:**
- `WorkflowLoader`, `WorkflowTrigger`
- `parse_workflow_json`, `extract_workflow_metadata`, `trigger_workflow_manually`, `get_execution_status`

---

## 4. `test_engine` Modülü

Sistemin uçtan uca ve birim testlerini kolaylaştıran, simüle edilmiş bir execution engine ve test queue altyapısı.

- **mock_engine.py**: MockExecutionEngine ile task execution'ı simüle eder, predefined sonuçlar döner.
- **test_queue.py**: TestQueueSystem ile in-memory input/output queue yönetimi ve monitoring.
- **test_scenarios.py**: Farklı test workflow'ları ve predefined result mapping.
- **test_scheduler.py**: TestEnabledQueueMonitor ve TestScheduler ile gerçek scheduler davranışını simüle eden test ortamı.
- **end_to_end_test.py**: EndToEndTestSuite ile tüm sistemi baştan sona test eden kapsamlı testler.

**Öne Çıkan Sınıf/Fonksiyonlar:**
- `MockExecutionEngine`, `TestQueueSystem`, `TestScheduler`, `EndToEndTestSuite`
- `create_test_workflow`, `run_end_to_end_test`, `get_predefined_results`

---

Her modülün içinde detaylı docstring ve fonksiyon açıklamaları mevcuttur. Daha fazla detay için ilgili dosyaların başındaki açıklamaları inceleyebilirsiniz. 