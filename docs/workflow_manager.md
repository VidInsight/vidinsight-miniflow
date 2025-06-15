# Miniflow Workflow Manager Modülü Dökümantasyonu

## Amaç ve Kapsam
Workflow'ların yüklenmesi (JSON'dan), doğrulanması, parametre mapping işlemleri ve tetiklenmesi için kullanılır.

## Ana Dosyalar ve Sınıflar

- **loader.py**: `WorkflowLoader` ile JSON workflow dosyasını okur, validate eder, veritabanına yükler.
- **trigger.py**: `WorkflowTrigger` ile workflow'u tetikler, execution başlatır, durum sorgular.
- **utils/workflow_parser.py**: `parse_workflow_json`, `extract_workflow_metadata`, `extract_nodes`, `extract_triggers`: JSON parsing ve validation.

## Temel Fonksiyonlar ve Kullanım

### Workflow Yükleme
```python
from miniflow.workflow_manager.loader import WorkflowLoader
loader = WorkflowLoader("mydb.sqlite")
result = loader.load_workflow_from_file("workflow.json")
if result["success"]:
    print("Workflow yüklendi:", result["workflow_id"])
```

### Workflow Tetikleme
```python
from miniflow.workflow_manager.trigger import WorkflowTrigger
trigger = WorkflowTrigger("mydb.sqlite")
res = trigger.trigger_workflow_manually(workflow_id)
if res["success"]:
    print("Workflow tetiklendi, execution id:", res["execution_id"])
```

### İpuçları
- Parametre mapping (node_name.variable → node_id.variable) otomatik yapılır.
- JSON validation hataları detaylı olarak döner.
- Tetikleme sonrası execution ve task durumları sorgulanabilir.

---

Daha fazla detay için ilgili dosyaların başındaki docstring açıklamalarına bakabilirsiniz. 