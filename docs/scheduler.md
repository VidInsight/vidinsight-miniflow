# Miniflow Scheduler Modülü Dökümantasyonu

## Amaç ve Kapsam
Workflow task'larının otomatik olarak işlenmesini, sıraya alınmasını ve sonuçların izlenmesini sağlar. Gerçek zamanlı veya periyodik task işleme için kullanılır.

## Ana Dosyalar ve Sınıflar

- **queue_monitoring.py**: `QueueMonitor` ile execution queue'yu izler, hazır task'ları işler.
- **result_monitoring.py**: `ResultMonitor` ile tamamlanan task sonuçlarını alır ve workflow orchestration'a besler.
- **scheduler.py**: `WorkflowScheduler` ile QueueMonitor ve ResultMonitor'u koordine eder, health check ve auto-recovery içerir.
- **context_manager.py**: Parametrelerdeki placeholder'ları çözer, context oluşturur.

## Temel Fonksiyonlar ve Kullanım

### Scheduler Başlatma
```python
from miniflow.scheduler.scheduler import WorkflowScheduler
scheduler = WorkflowScheduler("mydb.sqlite")
scheduler.start()
```

### Queue Monitor Manuel Kullanımı
```python
from miniflow.scheduler.queue_monitoring import QueueMonitor
qm = QueueMonitor("mydb.sqlite")
qm.start()
# ... sistem çalışırken otomatik task işler ...
qm.stop()
```

### Result Monitor Manuel Kullanımı
```python
from miniflow.scheduler.result_monitoring import ResultMonitor
rm = ResultMonitor("mydb.sqlite")
rm.start()
# ... sonuçlar otomatik işlenir ...
rm.stop()
```

### İpuçları
- `send_to_input_queue` fonksiyonu gerçek execution engine ile entegre edilebilir.
- `get_ready_tasks` ile sadece çalışmaya hazır task'lar alınır.
- Scheduler'ın health check özelliği ile otomatik yeniden başlatma yapılabilir.

---

Daha fazla detay için ilgili dosyaların başındaki docstring açıklamalarına bakabilirsiniz. 