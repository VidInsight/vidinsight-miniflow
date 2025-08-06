# MiniFlow Audit System Documentation

## 📋 İçindekiler
- [Genel Bakış](#genel-bakış)
- [Sistem Mimarisi](#sistem-mimarisi)
- [Kullanım Rehberi](#kullanım-rehberi)
- [Yapılandırma](#yapılandırma)
- [Performance & Best Practices](#performance--best-practices)
- [Troubleshooting](#troubleshooting)

---

## 🎯 Genel Bakış

MiniFlow Audit Sistemi, veritabanı operasyonlarının otomatik olarak izlenmesi ve kaydedilmesi için esnek, performans odaklı bir çözüm sunar.

### ✨ Temel Özellikler
- **Opt-in Design**: Audit sadece ihtiyaç duyulan yerlerde aktif
- **Environment-based Control**: Tek environment variable ile kontrol
- **Zero Performance Impact**: Audit kapalıyken hiç overhead yok
- **Automatic Change Tracking**: Old/new values otomatik kaydedilir
- **Production Ready**: Error handling ve fallback mekanizmaları

### 🏗️ Audit Edilen Operasyonlar
- **CREATE**: Yeni kayıt oluşturma
- **UPDATE**: Mevcut kayıt güncelleme  
- **DELETE**: Kayıt silme
- **ARCHIVE**: Kayıt arşivleme

---

## 🏛️ Sistem Mimarisi

### 📊 Bileşenler

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Decorators    │    │   AuditMixin    │    │  AuditLogCRUD   │
│  @audit_create  │────│   _init_audit   │────│   log_action    │
│  @audit_update  │    │ _create_audit_  │    │                 │
│  @audit_delete  │    │      log        │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Environment Control                          │
│              MINIFLOW_ENABLE_AUDIT=true/false                   │
└─────────────────────────────────────────────────────────────────┘
```

### 🔄 Çalışma Akışı

1. **Decorator Application Time**:
   - Environment variable kontrol edilir
   - Audit kapalıysa decorator bypass edilir
   - Audit açıksa wrapper function uygulanır

2. **Runtime**:
   - Business method çalışır
   - Old values kaydedilir (UPDATE/DELETE için)
   - New values kaydedilir (CREATE/UPDATE için)
   - Audit log veritabanına yazılır

3. **Error Handling**:
   - Audit hatası business logic'i durdurmaz
   - Hata loglanır ve devam edilir

---

## 📖 Kullanım Rehberi

### 🚀 Temel Kullanım

#### 1. CRUD Sınıfında Audit Aktifleştirme

```python
from miniflow.database_manager.crud.base_crud import BaseCRUD
from miniflow.database_manager.decorators import AuditMixin, audit_create, audit_update, audit_delete
from miniflow.database_manager.models import Workflow

class WorkflowCRUD(BaseCRUD[Workflow], AuditMixin):
    def __init__(self):
        super().__init__(Workflow)
        self._init_audit()  # Audit capability ekle
    
    @audit_create("workflows")
    def create(self, session, **kwargs):
        return super().create(session, **kwargs)
    
    @audit_update("workflows")
    def set_priority(self, session, workflow_id, priority):
        workflow = self.find_by_id(session, workflow_id)
        workflow.priority = priority
        session.flush()
        return workflow
    
    @audit_delete("workflows")
    def delete(self, session, workflow_id):
        return super().delete(session, workflow_id)
```

#### 2. Audit Olmayan CRUD Sınıfı

```python
class NodeCRUD(BaseCRUD[Node]):  # AuditMixin YOK
    def __init__(self):
        super().__init__(Node)
        # Audit capability yok - performans optimized
    
    def update_position(self, session, node_id, x, y):
        # High-frequency operation, audit gerekli değil
        node = self.find_by_id(session, node_id)
        node.position_x = x
        node.position_y = y
        session.flush()
        return node
```

### 🎛️ Decorator'lar

#### @audit_create(table_name)
Yeni kayıt oluşturma operasyonlarını audit eder.

```python
@audit_create("workflows")
def create_workflow(self, session, **data):
    workflow = self.create(session, **data)
    return workflow

# Audit Log:
# - action: CREATE
# - old_values: null
# - new_values: {id, name, description, ...}
```

#### @audit_update(table_name)  
Kayıt güncelleme operasyonlarını audit eder.

```python
@audit_update("workflows")
def set_status(self, session, workflow_id, new_status):
    workflow = self.find_by_id(session, workflow_id)
    workflow.status = new_status
    session.flush()
    return workflow

# Audit Log:
# - action: UPDATE  
# - old_values: {status: "draft", ...}
# - new_values: {status: "active", ...}
```

#### @audit_delete(table_name)
Kayıt silme operasyonlarını audit eder.

```python
@audit_delete("workflows")
def delete_workflow(self, session, workflow_id):
    workflow = self.find_by_id(session, workflow_id)
    session.delete(workflow)
    session.flush()
    return True

# Audit Log:
# - action: DELETE
# - old_values: {id, name, status, ...}
# - new_values: null
```

---

## ⚙️ Yapılandırma

### 🌍 Environment Variable

```bash
# Audit sistemi AKTIF (default)
export MINIFLOW_ENABLE_AUDIT=true

# Audit sistemi KAPALI  
export MINIFLOW_ENABLE_AUDIT=false
```

### 🏗️ Deployment Senaryoları

#### Development Environment
```bash
# Hızlı iterasyon için audit kapat
export MINIFLOW_ENABLE_AUDIT=false
```

#### Staging Environment  
```bash
# Gerçekçi test için audit aç
export MINIFLOW_ENABLE_AUDIT=true
```

#### Production - High Performance
```bash
# Performance kritik ise audit kapat
export MINIFLOW_ENABLE_AUDIT=false
```

#### Production - Compliance
```bash
# Yasal gereklilikler için audit aç
export MINIFLOW_ENABLE_AUDIT=true
```

### 🔧 Selective Auditing

Kritik operasyonlarda audit, sık kullanılan operasyonlarda audit yok:

```python
class ExecutionCRUD(BaseCRUD[Execution], AuditMixin):
    def __init__(self):
        super().__init__(Execution)
        self._init_audit()
    
    @audit_create("executions")  # AUDIT: Critical business event
    def start_execution(self, session, workflow_id):
        execution = self.create(session, 
            workflow_id=workflow_id,
            status=ExecutionStatus.RUNNING
        )
        return execution
    
    def update_heartbeat(self, session, execution_id):
        # NO AUDIT: High-frequency operation
        execution = self.find_by_id(session, execution_id)
        execution.last_heartbeat = datetime.utcnow()
        session.flush()
        return execution
```

---

## 🚀 Performance & Best Practices

### 📊 Performance Impact

Test sonuçları (100 operasyon):
- **Audit KAPALI**: 6.1ms/op  
- **Audit AÇIK**: 10.6ms/op
- **Overhead**: %73

### ✅ Best Practices

#### 1. Strategic Audit Placement
```python
# ✅ AUDIT UYGUN: Business-critical operations
@audit_update("workflows")
def archive_workflow(self, session, workflow_id):
    # Compliance için kritik
    pass

# ❌ AUDIT UYGUNSUZ: High-frequency operations  
def update_execution_heartbeat(self, session, execution_id):
    # Her 5 saniyede bir çalışır, audit gereksiz
    pass
```

#### 2. Environment-based Strategy
```python
# Production config
if ENVIRONMENT == "production":
    MINIFLOW_ENABLE_AUDIT = COMPLIANCE_REQUIRED
elif ENVIRONMENT == "development":
    MINIFLOW_ENABLE_AUDIT = False
else:
    MINIFLOW_ENABLE_AUDIT = True
```

#### 3. Table-level Granularity
```python
# Critical tables → Full audit
class WorkflowCRUD(BaseCRUD[Workflow], AuditMixin): pass

# Operational tables → No audit  
class HeartbeatCRUD(BaseCRUD[Heartbeat]): pass
```

### 💾 Storage Considerations

#### Audit Log Growth
- Ortalama audit record: ~2KB
- 1000 operasyon/gün = ~2MB/gün
- Yıllık büyüme: ~730MB

#### Retention Policy
```python
# Audit log temizleme (önerilen)
def cleanup_audit_logs(older_than_days=90):
    cutoff_date = datetime.utcnow() - timedelta(days=older_than_days)
    session.query(AuditLog).filter(
        AuditLog.created_at < cutoff_date
    ).delete()
```

---

## 🔍 Troubleshooting

### ❌ Yaygın Sorunlar

#### 1. Audit Log Oluşturulmuyor

**Belirti**: Decorator'lar çalışıyor ama audit log yok

**Çözümler**:
```python
# Environment variable kontrol et
print(f"AUDIT_ENABLED: {AUDIT_ENABLED}")

# AuditMixin eklenmiş mi kontrol et
print(f"Has AuditMixin: {'AuditMixin' in str(crud.__class__.__mro__)}")

# _init_audit() çağrılmış mı kontrol et
print(f"Has _audit_crud: {hasattr(crud, '_audit_crud')}")
```

#### 2. Performance Problemi

**Belirti**: Audit açıkken sistem yavaş

**Çözümler**:
```python
# 1. Selective audit uygula
class HighFrequencyCRUD(BaseCRUD[Model]):  # AuditMixin YOK
    pass

# 2. Environment variable ile kapat
export MINIFLOW_ENABLE_AUDIT=false

# 3. Kritik operasyonlarda audit kapat
def frequent_operation(self, session, ...):
    # @audit_update decorator'ını kaldır
    pass
```

#### 3. Circular Import Error

**Belirti**: `ImportError: cannot import name 'AuditLogCRUD'`

**Çözüm**: Lazy import kullanılıyor, restart gerekebilir
```python
# _init_audit() method'unda lazy import var
def _init_audit(self):
    if AUDIT_ENABLED:
        from .crud.audit_log_crud import AuditLogCRUD  # Lazy import
        self._audit_crud = AuditLogCRUD()
```

### 🔧 Debug Commands

```python
# Audit durumu kontrol et
from miniflow.database_manager.decorators import AUDIT_ENABLED
print(f"Global audit enabled: {AUDIT_ENABLED}")

# CRUD audit durumu
crud = WorkflowCRUD()
print(f"CRUD has audit: {hasattr(crud, '_audit_crud')}")
print(f"Audit CRUD type: {type(crud._audit_crud)}")

# Audit log sayısı
audit_crud = AuditLogCRUD()
with engine.get_session_context() as session:
    count = audit_crud.count(session)
    print(f"Total audit logs: {count}")
```

---

## 📝 Örnek Kullanım Senaryoları

### 🏢 Enterprise Compliance
```python
# Tüm kritik operasyonlarda audit
class ComplianceWorkflowCRUD(BaseCRUD[Workflow], AuditMixin):
    def __init__(self):
        super().__init__(Workflow)
        self._init_audit()
    
    @audit_create("workflows")
    def create(self, session, **kwargs): pass
    
    @audit_update("workflows")  
    def update(self, session, record_id, **kwargs): pass
    
    @audit_delete("workflows")
    def delete(self, session, record_id): pass
```

### 🚀 High-Performance Application
```python
# Sadece business-critical operasyonlarda audit
class PerformanceWorkflowCRUD(BaseCRUD[Workflow], AuditMixin):
    def __init__(self):
        super().__init__(Workflow) 
        self._init_audit()
    
    @audit_update("workflows")  # Sadece bu audit'li
    def archive(self, session, workflow_id): pass
    
    def update_metadata(self, session, workflow_id, metadata):
        # High-frequency, audit yok
        pass
```

### 🧪 Development Environment  
```python
# Audit capability var ama environment ile kontrol
class DevWorkflowCRUD(BaseCRUD[Workflow], AuditMixin):
    def __init__(self):
        super().__init__(Workflow)
        self._init_audit()  # MINIFLOW_ENABLE_AUDIT=false ise çalışmaz
    
    @audit_update("workflows")  # Environment ile kontrol
    def any_operation(self, session, ...): pass
```

---

## 🎯 Sonuç

MiniFlow Audit Sistemi, modern enterprise uygulamaların ihtiyaç duyduğu esnekliği ve performansı sunar:

- ✅ **Flexible**: İhtiyaç duyulan yerlerde audit
- ✅ **Performant**: Audit kapalıyken zero overhead  
- ✅ **Production Ready**: Error handling ve monitoring
- ✅ **Developer Friendly**: Basit decorator interface
- ✅ **Ops Friendly**: Environment variable control

**Environment variable ile tek noktadan kontrol**, **decorator'lar ile kolay uygulama** ve **mixin ile optional capability** sayesinde audit sistemi hem güçlü hem de praktik bir çözüm sunar.