# MiniFlow Kullanım Rehberi

## İçindekiler
1. [Giriş](#giriş)
2. [Kurulum](#kurulum)
3. [Temel Kullanım](#temel-kullanım)
4. [İş Akışı Yönetimi](#iş-akışı-yönetimi)
5. [Zamanlama ve Kuyruk Yönetimi](#zamanlama-ve-kuyruk-yönetimi)
6. [Test Motoru](#test-motoru)
7. [Hata Yönetimi](#hata-yönetimi)

## Giriş

MiniFlow, iş akışlarını yönetmek, zamanlamak ve test etmek için tasarlanmış güçlü bir sistemdir. Bu rehber, sistemin temel özelliklerini ve nasıl kullanılacağını açıklar.

## Kurulum

1. Gerekli paketleri yükleyin:
```bash
pip install -r requirements.txt
```

2. Veritabanı bağlantısını yapılandırın:
```python
from miniflow.database import DatabaseManager

db = DatabaseManager(
    host="localhost",
    port=5432,
    database="miniflow",
    user="kullanici",
    password="sifre"
)
```

## Temel Kullanım

### İş Akışı Oluşturma

```python
from miniflow.workflow_manager import WorkflowManager

workflow = {
    "name": "ornek_akıs",
    "steps": [
        {
            "name": "adim1",
            "type": "task",
            "handler": "ornek_fonksiyon"
        }
    ]
}

manager = WorkflowManager()
manager.create_workflow(workflow)
```

### İş Akışını Çalıştırma

```python
workflow_id = manager.run_workflow("ornek_akıs")
```

## İş Akışı Yönetimi

### Adım Ekleme
```python
manager.add_step("ornek_akıs", {
    "name": "yeni_adim",
    "type": "task",
    "handler": "yeni_fonksiyon"
})
```

### Durum Kontrolü
```python
status = manager.get_workflow_status(workflow_id)
```

## Zamanlama ve Kuyruk Yönetimi

### Zamanlanmış Görev Oluşturma
```python
from miniflow.scheduler import WorkflowScheduler

scheduler = WorkflowScheduler()
scheduler.schedule_workflow(
    workflow_id="ornek_akıs",
    schedule="0 0 * * *"  # Her gün gece yarısı
)
```

### Kuyruk İzleme
```python
from miniflow.scheduler import QueueMonitor

monitor = QueueMonitor()
queue_status = monitor.get_queue_status()
```

## Test Motoru

### Test Senaryosu Oluşturma
```python
from miniflow.test_engine import TestEngine

test_engine = TestEngine()
test_engine.create_test_case({
    "name": "temel_test",
    "workflow": "ornek_akıs",
    "expected_results": {...}
})
```

### Test Çalıştırma
```python
results = test_engine.run_tests("temel_test")
```

## Hata Yönetimi

### Hata Yakalama
```python
try:
    manager.run_workflow("ornek_akıs")
except WorkflowError as e:
    print(f"Hata: {e.message}")
```

### Loglama
```python
from miniflow.logger import Logger

logger = Logger()
logger.error("Hata mesajı", extra={"workflow_id": workflow_id})
```

## İpuçları ve En İyi Uygulamalar

1. Her zaman iş akışlarınızı test edin
2. Hata durumlarını düzgün şekilde yönetin
3. Düzenli olarak logları kontrol edin
4. Zamanlanmış görevleri dikkatli planlayın
5. Veritabanı bağlantılarını düzgün kapatın

## Sık Karşılaşılan Sorunlar ve Çözümleri

1. **Veritabanı Bağlantı Hatası**
   - Bağlantı bilgilerini kontrol edin
   - Veritabanı servisinin çalıştığından emin olun

2. **Zamanlama Hatası**
   - Cron ifadesinin doğru formatta olduğunu kontrol edin
   - Sistem saatini kontrol edin

3. **İş Akışı Durma**
   - Logları kontrol edin
   - Bağımlılıkları doğrulayın 