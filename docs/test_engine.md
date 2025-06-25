# Miniflow Test Engine Modülü Dökümantasyonu

## Amaç ve Kapsam
Sistemin uçtan uca ve birim testlerini kolaylaştıran, simüle edilmiş bir execution engine ve test queue altyapısı sağlar.

## Ana Dosyalar ve Sınıflar

- **mock_engine.py**: `MockExecutionEngine` ile task execution'ı simüle eder, predefined sonuçlar döner.
- **test_queue.py**: `TestQueueSystem` ile in-memory input/output queue yönetimi ve monitoring.
- **test_scenarios.py**: `create_test_workflow`, `create_simple_test_workflow`, `get_predefined_results`: Test workflow'ları ve sonuçları.
- **test_scheduler.py**: `TestScheduler`, `TestEnabledQueueMonitor`: Gerçek scheduler davranışını simüle eden test ortamı.
- **end_to_end_test.py**: `EndToEndTestSuite`: Tüm sistemi baştan sona test eden kapsamlı testler.

## Temel Fonksiyonlar ve Kullanım

### Test Workflow Oluşturma ve Kaydetme
```python
from miniflow.test_engine.test_scenarios import create_test_workflow, save_test_workflow_to_file
workflow = create_test_workflow()
save_test_workflow_to_file(workflow, "test_workflow.json")
```

### Mock Engine ile Task Çalıştırma
```python
from miniflow.test_engine.mock_engine import MockExecutionEngine
engine = MockExecutionEngine()
result = engine.execute_task({"node_id": "n1", "type": "extract", "params": {}})
print(result)
```

### End-to-End Test Çalıştırma
```python
from miniflow.test_engine.end_to_end_test import run_end_to_end_test
summary = run_end_to_end_test()
print(summary)
```

### İpuçları
- Test engine gerçek execution engine olmadan tüm akışı test etmenizi sağlar.
- Test queue ile task ve result akışını izleyebilirsiniz.
- End-to-end testler ile sistemin bütünlüğünü kolayca doğrulayabilirsiniz.

---

Daha fazla detay için ilgili dosyaların başındaki docstring açıklamalarına bakabilirsiniz. 