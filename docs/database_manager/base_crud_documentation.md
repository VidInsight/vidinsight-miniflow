# BaseCRUD Class - Comprehensive Documentation

## Overview

`BaseCRUD` is a generic base class that provides type-safe and performance-optimized CRUD (Create, Read, Update, Delete) operations for all entity models in the Miniflow system. It uses SQLAlchemy ORM and Python's generic programming features to ensure type safety and code reusability.

## Architecture

```python
class BaseCRUD(Generic[ModelType]):
    """
    Generic base CRUD class for all entity-specific CRUD operations.
    Provides type-safe CRUD operations with performance optimizations.
    """
```

### Type Safety
- Uses `TypeVar` for generic type constraints
- Bound to SQLAlchemy's `DeclarativeMeta` 
- Provides compile-time type checking
- Ensures return types match the model type

### Performance Features
- Memory protection with configurable limits
- Bulk operations for high-throughput scenarios
- Optimized queries with proper indexing
- Efficient batch processing

---

## BASIC OPERATIONS

### 0. __init__()

**Tanım:** BaseCRUD sınıfını belirli bir model tipi ile başlatır.

**Params:**
- `model: type[ModelType]` - CRUD işlemleri yapılacak SQLAlchemy model sınıfı

**Return:**
- `None` - Constructor fonksiyon

**Raises:**
- Yok

**Example Usage:**
```python
# Workflow için CRUD instance oluşturma
workflow_crud = BaseCRUD(Workflow)

# Node için CRUD instance oluşturma
node_crud = BaseCRUD(Node)

# Script için CRUD instance oluşturma
script_crud = BaseCRUD(Script)

# Generic type ile kullanım
from typing import TypeVar
T = TypeVar('T')
def create_crud(model_class: type[T]) -> BaseCRUD[T]:
    return BaseCRUD(model_class)

workflow_crud = create_crud(Workflow)
```

---

### 1. create()

**Tanım:** Yeni bir entity kaydı oluşturur ve veritabanına ekler.

**Params:**
- `session: Session` - SQLAlchemy database session
- `**model_data` - Entity için alanlar (keyword arguments)

**Return:**
- `ModelType` - Oluşturulan entity instance'ı

**Raises:**
- `ValueError` - Hiç veri sağlanmadığında

**Example Usage:**
```python
# Workflow oluşturma
workflow_crud = BaseCRUD(Workflow)
workflow = workflow_crud.create(
    session,
    name="Data Pipeline",
    description="Process customer data",
    priority=75
)
print(f"Created workflow: {workflow.id}")

# Node oluşturma  
node_crud = BaseCRUD(Node)
node = node_crud.create(
    session,
    name="Data Loader",
    workflow_id=workflow.id,
    script_id="SC123456789",
    max_retries=3
)
```

---

### 2. find_by_id()

**Tanım:** ID ile belirli bir entity kaydını bulur.

**Params:**
- `session: Session` - SQLAlchemy database session
- `record_id: Union[str, int]` - Aranacak entity ID'si

**Return:**
- `Optional[ModelType]` - Bulunan entity instance'ı veya None

**Raises:**
- `ValueError` - Entity bulunamadığında

**Example Usage:**
```python
# ID ile workflow bulma
workflow = workflow_crud.find_by_id(session, "WF123456789")
print(f"Found workflow: {workflow.name}")

# ID ile node bulma
node = node_crud.find_by_id(session, "ND987654321")
print(f"Node belongs to workflow: {node.workflow_id}")

# Hata yakalama
try:
    missing_workflow = workflow_crud.find_by_id(session, "NONEXISTENT")
except ValueError as e:
    print(f"Error: {e}")
```

---

### 3. find_by_name()

**Tanım:** Name alanı ile entity kaydını bulur.

**Params:**
- `session: Session` - SQLAlchemy database session
- `name: str` - Aranacak entity adı

**Return:**
- `Optional[ModelType]` - Bulunan entity instance'ı veya None

**Raises:**
- `ValueError` - Model'de 'name' alanı yoksa veya entity bulunamadığında

**Example Usage:**
```python
# İsim ile workflow bulma
workflow = workflow_crud.find_by_name(session, "Data Pipeline")
print(f"Workflow ID: {workflow.id}")

# İsim ile script bulma
script_crud = BaseCRUD(Script)
script = script_crud.find_by_name(session, "Data Processor")
print(f"Script path: {script.script_path}")

# Name alanı olmayan model için hata
try:
    audit_crud = BaseCRUD(AuditLog)  # AuditLog'da name alanı yok
    audit = audit_crud.find_by_name(session, "test")
except ValueError as e:
    print(f"Error: {e}")
```

---

### 4. update()

**Tanım:** Var olan bir entity kaydını günceller.

**Params:**
- `session: Session` - SQLAlchemy database session
- `record_id: Union[str, int]` - Güncellenecek entity ID'si
- `**model_data` - Güncellenecek alanlar (keyword arguments)

**Return:**
- `ModelType` - Güncellenmiş entity instance'ı

**Raises:**
- `ValueError` - Hiç veri sağlanmadığında veya entity bulunamadığında

**Example Usage:**
```python
# Workflow güncelleme
updated_workflow = workflow_crud.update(
    session,
    "WF123456789",
    priority=90,
    description="Updated description"
)
print(f"Updated priority: {updated_workflow.priority}")

# Node parametrelerini güncelleme
updated_node = node_crud.update(
    session,
    "ND987654321",
    params={"batch_size": 1000, "timeout": 300},
    max_retries=5
)

# Mevcut olmayan alan göz ardı edilir
workflow_crud.update(session, "WF123456789", nonexistent_field="value")
```

---

### 5. delete()

**Tanım:** Belirli bir entity kaydını siler.

**Params:**
- `session: Session` - SQLAlchemy database session
- `record_id: Union[str, int]` - Silinecek entity ID'si

**Return:**
- `ModelType` - Silinen entity instance'ı

**Raises:**
- `ValueError` - Entity bulunamadığında

**Example Usage:**
```python
# Workflow silme (CASCADE ile bağımlı kayıtlar da silinir)
deleted_workflow = workflow_crud.delete(session, "WF123456789")
print(f"Deleted workflow: {deleted_workflow.name}")

# Node silme
deleted_node = node_crud.delete(session, "ND987654321")
print(f"Deleted node: {deleted_node.name}")

# Transaction içinde silme
try:
    with session.begin():
        workflow_crud.delete(session, "WF111111111")
        print("Workflow deleted successfully")
except Exception as e:
    print(f"Delete failed: {e}")
```

---

## QUERY OPERATIONS

### 6. get_all()

**Tanım:** Tüm entity kayıtlarını pagination ve ordering ile getirir.

**Params:**
- `session: Session` - SQLAlchemy database session
- `skip: int = 0` - Atlanacak kayıt sayısı (pagination)
- `limit: int = 100` - Maksimum döndürülecek kayıt sayısı (max: 1000)
- `order_by_field: str = None` - Sıralama alanı
- `desc: bool = False` - Azalan sıralama flag'i

**Return:**
- `List[ModelType]` - Entity kayıtları listesi

**Raises:**
- Yok (boş liste döner)

**Example Usage:**
```python
# Tüm workflow'ları getir (ilk 100)
workflows = workflow_crud.get_all(session)
print(f"Total workflows: {len(workflows)}")

# Pagination ile workflow'lar
page_2_workflows = workflow_crud.get_all(session, skip=100, limit=50)

# Priority'ye göre azalan sıralama
sorted_workflows = workflow_crud.get_all(
    session, 
    order_by_field="priority", 
    desc=True, 
    limit=20
)

# Created_at'e göre en yeni kayıtlar
recent_executions = execution_crud.get_all(
    session,
    order_by_field="created_at",
    desc=True,
    limit=10
)
```

---

### 7. count()

**Tanım:** Toplam entity kayıt sayısını getirir.

**Params:**
- `session: Session` - SQLAlchemy database session

**Return:**
- `int` - Toplam kayıt sayısı

**Raises:**
- Yok

**Example Usage:**
```python
# Toplam workflow sayısı
total_workflows = workflow_crud.count(session)
print(f"Total workflows in database: {total_workflows}")

# Toplam execution sayısı
total_executions = execution_crud.count(session)
print(f"Total executions: {total_executions}")

# Pagination için sayı hesaplama
page_size = 50
total_pages = (total_workflows + page_size - 1) // page_size
print(f"Total pages: {total_pages}")
```

---

### 8. exists()

**Tanım:** Belirli ID'ye sahip entity'nin var olup olmadığını kontrol eder.

**Params:**
- `session: Session` - SQLAlchemy database session
- `record_id: Union[str, int]` - Kontrol edilecek entity ID'si

**Return:**
- `bool` - Entity var ise True, yoksa False

**Raises:**
- Yok

**Example Usage:**
```python
# Workflow var mı kontrol
if workflow_crud.exists(session, "WF123456789"):
    print("Workflow exists")
else:
    print("Workflow not found")

# Bulk kontrolde kullanım
workflow_ids = ["WF111", "WF222", "WF333"]
existing_workflows = [
    wf_id for wf_id in workflow_ids 
    if workflow_crud.exists(session, wf_id)
]
print(f"Existing workflows: {existing_workflows}")

# Entity oluşturmadan önce kontrol
if not node_crud.exists(session, "ND999999999"):
    node = node_crud.create(session, name="New Node", workflow_id="WF123")
```

---

### 9. filter()

**Tanım:** Çoklu filtreleme kriterleri ile entity kayıtlarını getirir.

**Params:**
- `session: Session` - SQLAlchemy database session
- `filters: Dict[str, Any]` - Filtreleme kriterleri
- `skip: int = 0` - Atlanacak kayıt sayısı
- `limit: int = 100` - Maksimum kayıt sayısı
- `order_by_field: str = None` - Sıralama alanı

**Return:**
- `List[ModelType]` - Filtrelenmiş entity listesi

**Raises:**
- `ValueError` - Geçersiz alan adı sağlandığında

**Example Usage:**
```python
# Status ve priority'ye göre filtreleme
active_high_priority = workflow_crud.filter(
    session,
    filters={
        "status": WorkflowStatus.ACTIVE,
        "priority": 90
    },
    limit=50
)

# Workflow'a ait node'ları filtreleme
workflow_nodes = node_crud.filter(
    session,
    filters={"workflow_id": "WF123456789"},
    order_by_field="name"
)

# Execution status filtreleme
running_executions = execution_crud.filter(
    session,
    filters={"status": ExecutionStatus.RUNNING},
    order_by_field="created_at",
    limit=20
)
```

---

### 10. count_filtered()

**Tanım:** Filtreleme kriterlerine uyan kayıt sayısını getirir.

**Params:**
- `session: Session` - SQLAlchemy database session
- `filters: Dict[str, Any]` - Filtreleme kriterleri

**Return:**
- `int` - Filtrelenmiş kayıt sayısı

**Raises:**
- `ValueError` - Geçersiz alan adı sağlandığında

**Example Usage:**
```python
# Aktif workflow sayısı
active_count = workflow_crud.count_filtered(
    session,
    filters={"status": WorkflowStatus.ACTIVE}
)
print(f"Active workflows: {active_count}")

# Belirli workflow'daki node sayısı
node_count = node_crud.count_filtered(
    session,
    filters={"workflow_id": "WF123456789"}
)
print(f"Nodes in workflow: {node_count}")

# Başarısız execution sayısı
failed_count = execution_crud.count_filtered(
    session,
    filters={"status": ExecutionStatus.FAILED}
)
```

---

### 11. find_by_field()

**Tanım:** Tek bir alan değeri ile entity kayıtlarını bulur.

**Params:**
- `session: Session` - SQLAlchemy database session
- `field_name: str` - Aranacak alan adı
- `value: Any` - Aranacak değer
- `limit: int = 100` - Maksimum kayıt sayısı

**Return:**
- `List[ModelType]` - Bulunan entity listesi

**Raises:**
- `ValueError` - Geçersiz alan adı sağlandığında

**Example Usage:**
```python
# Priority değeri ile workflow bulma
high_priority = workflow_crud.find_by_field(
    session, 
    "priority", 
    90, 
    limit=10
)

# Script ID ile node'ları bulma
script_nodes = node_crud.find_by_field(
    session,
    "script_id",
    "SC123456789"
)

# Language ile script'leri bulma
python_scripts = script_crud.find_by_field(
    session,
    "language",
    ScriptType.PYTHON,
    limit=50
)
```

---

## BULK OPERATIONS

### 12. select_in_bulk()

**Tanım:** Birden fazla ID ile entity kayıtlarını toplu olarak getirir.

**Params:**
- `session: Session` - SQLAlchemy database session
- `ids: List[Union[str, int]]` - Getirilecek entity ID'leri listesi

**Return:**
- `List[ModelType]` - Bulunan entity listesi

**Raises:**
- Yok (boş liste döner)

**Example Usage:**
```python
# Birden fazla workflow'ı toplu getir
workflow_ids = ["WF111", "WF222", "WF333"]
workflows = workflow_crud.select_in_bulk(session, workflow_ids)
print(f"Found {len(workflows)} workflows")

# Node'ları toplu getir
node_ids = ["ND111", "ND222", "ND333", "ND444"]
nodes = node_crud.select_in_bulk(session, node_ids)

# Mevcut olmayan ID'ler göz ardı edilir
mixed_ids = ["WF111", "NONEXISTENT", "WF222"]
found_workflows = workflow_crud.select_in_bulk(session, mixed_ids)
# Sadece var olan WF111 ve WF222 döner
```

---

### 13. truncate()

**Tanım:** Tablodaki tüm kayıtları siler.

**Params:**
- `session: Session` - SQLAlchemy database session

**Return:**
- `int` - Silinen kayıt sayısı

**Raises:**
- Yok

**Example Usage:**
```python
# ⚠️ DİKKAT: Tüm workflow'ları siler!
deleted_count = workflow_crud.truncate(session)
print(f"Deleted {deleted_count} workflows")

# Test veritabanını temizleme
if is_test_environment():
    node_crud.truncate(session)
    edge_crud.truncate(session)
    workflow_crud.truncate(session)
    print("Test database cleared")

# Transaction ile güvenli kullanım
try:
    with session.begin():
        count = execution_crud.truncate(session)
        print(f"Cleared {count} executions")
except Exception as e:
    print(f"Truncate failed: {e}")
```

---

### 14. bulk_create()

**Tanım:** Birden fazla entity kaydını toplu olarak oluşturur.

**Params:**
- `session: Session` - SQLAlchemy database session
- `objects_data: List[Dict[str, Any]]` - Oluşturulacak entity verilerinin listesi

**Return:**
- `List[Dict[str, Any]]` - Oluşturulan entity verilerinin listesi (ID'ler otomatik generate edilir)

**Raises:**
- `ValueError` - ID generation metodu bulunamadığında

**Example Usage:**
```python
# Bulk workflow oluşturma
bulk_workflows = [
    {"name": "Pipeline 1", "priority": 80},
    {"name": "Pipeline 2", "priority": 70},
    {"name": "Pipeline 3", "priority": 90}
]
created = workflow_crud.bulk_create(session, bulk_workflows)
print(f"Created {len(created)} workflows")

# Bulk node oluşturma
bulk_nodes = [
    {"name": "Node 1", "workflow_id": "WF123", "max_retries": 3},
    {"name": "Node 2", "workflow_id": "WF123", "max_retries": 2},
    {"name": "Node 3", "workflow_id": "WF456", "max_retries": 5}
]
nodes = node_crud.bulk_create(session, bulk_nodes)

# ID'ler otomatik generate edilir
for node_data in nodes:
    print(f"Generated ID: {node_data['id']}")
```

---

### 15. bulk_update()

**Tanım:** Birden fazla entity kaydını toplu olarak günceller.

**Params:**
- `session: Session` - SQLAlchemy database session
- `updates: List[Dict[str, Any]]` - Güncellenecek veriler (id alanı zorunlu)

**Return:**
- `List[Dict[str, Any]]` - Güncellenen verilerinin listesi

**Raises:**
- `ValueError` - Update verilerinde 'id' alanı eksikse

**Example Usage:**
```python
# Bulk workflow güncelleme
bulk_updates = [
    {"id": "WF111", "priority": 95, "description": "Updated 1"},
    {"id": "WF222", "priority": 85, "description": "Updated 2"},
    {"id": "WF333", "priority": 75, "description": "Updated 3"}
]
updated = workflow_crud.bulk_update(session, bulk_updates)
print(f"Updated {len(updated)} workflows")

# Bulk node parameter güncelleme
node_updates = [
    {"id": "ND111", "max_retries": 10},
    {"id": "ND222", "timeout_seconds": 600},
    {"id": "ND333", "params": {"new_param": "value"}}
]
node_crud.bulk_update(session, node_updates)

# ID eksik olan güncelleme hatası
try:
    invalid_updates = [{"priority": 90}]  # ID yok
    workflow_crud.bulk_update(session, invalid_updates)
except ValueError as e:
    print(f"Error: {e}")
```

---

### 16. bulk_delete()

**Tanım:** Birden fazla entity kaydını toplu olarak siler.

**Params:**
- `session: Session` - SQLAlchemy database session
- `ids: List[Union[str, int]]` - Silinecek entity ID'leri

**Return:**
- `int` - Silinen kayıt sayısı

**Raises:**
- Yok

**Example Usage:**
```python
# Bulk workflow silme
workflow_ids = ["WF111", "WF222", "WF333"]
deleted_count = workflow_crud.bulk_delete(session, workflow_ids)
print(f"Deleted {deleted_count} workflows")

# Bulk node silme
node_ids = ["ND111", "ND222", "ND333", "ND444"]
node_deleted = node_crud.bulk_delete(session, node_ids)

# Mevcut olmayan ID'ler göz ardı edilir
mixed_ids = ["WF111", "NONEXISTENT", "WF222"]
actual_deleted = workflow_crud.bulk_delete(session, mixed_ids)
# Sadece var olan kayıtlar silinir

# Boş liste ile kullanım
empty_deleted = workflow_crud.bulk_delete(session, [])
print(f"Deleted from empty list: {empty_deleted}")  # 0
```

---

## OPTIMIZED OPERATIONS

### 17. check_name_exists()

**Tanım:** Belirli bir ismin veritabanında var olup olmadığını kontrol eder.

**Params:**
- `session: Session` - SQLAlchemy database session
- `name: str` - Kontrol edilecek isim
- `exclude_id: str = None` - Kontrolden hariç tutulacak entity ID'si

**Return:**
- `bool` - İsim var ise True, yoksa False

**Raises:**
- `ValueError` - Model'de 'name' alanı yoksa

**Example Usage:**
```python
# Workflow ismi var mı kontrol
if workflow_crud.check_name_exists(session, "Data Pipeline"):
    print("Workflow name already exists")
else:
    print("Name is available")

# Update sırasında kendi ID'sini hariç tutma
existing = workflow_crud.check_name_exists(
    session, 
    "New Pipeline", 
    exclude_id="WF123456789"
)

# Script ismi kontrolü
if not script_crud.check_name_exists(session, "Data Processor"):
    script = script_crud.create(session, name="Data Processor")

# Unique name validation
def validate_unique_name(crud, session, name, exclude_id=None):
    if crud.check_name_exists(session, name, exclude_id):
        raise ValueError(f"Name '{name}' already exists")
```

---

### 18. bulk_update_status()

**Tanım:** Birden fazla entity'nin status alanını toplu olarak günceller.

**Params:**
- `session: Session` - SQLAlchemy database session
- `ids: List[Union[str, int]]` - Güncellenecek entity ID'leri
- `status_field: str` - Status alanının adı
- `new_status: Any` - Yeni status değeri

**Return:**
- `int` - Güncellenen kayıt sayısı

**Raises:**
- `ValueError` - Status field adı sağlanmadığında veya geçersiz alan adında

**Example Usage:**
```python
# Bulk workflow status güncelleme
workflow_ids = ["WF111", "WF222", "WF333"]
updated_count = workflow_crud.bulk_update_status(
    session,
    workflow_ids,
    "status",
    WorkflowStatus.ACTIVE
)
print(f"Activated {updated_count} workflows")

# Bulk execution status güncelleme
execution_ids = ["EX111", "EX222"]
execution_crud.bulk_update_status(
    session,
    execution_ids,
    "status", 
    ExecutionStatus.CANCELLED
)

# Script test status güncelleme
script_ids = ["SC111", "SC222", "SC333"]
script_crud.bulk_update_status(
    session,
    script_ids,
    "test_status",
    ScriptTestStatus.PASSED
)
```

---

### 19. bulk_update_fields()

**Tanım:** Birden fazla entity'nin birden fazla alanını toplu olarak günceller.

**Params:**
- `session: Session` - SQLAlchemy database session
- `ids: List[Union[str, int]]` - Güncellenecek entity ID'leri
- `field_updates: Dict[str, Any]` - Güncellenecek alan-değer çiftleri

**Return:**
- `int` - Güncellenen kayıt sayısı

**Raises:**
- `ValueError` - Field updates sağlanmadığında veya geçersiz alan adında

**Example Usage:**
```python
# Bulk workflow fields güncelleme
workflow_ids = ["WF111", "WF222", "WF333"]
updated_count = workflow_crud.bulk_update_fields(
    session,
    workflow_ids,
    {
        "priority": 90,
        "is_active": True,
        "description": "Bulk updated"
    }
)
print(f"Updated {updated_count} workflows")

# Bulk node timeout güncelleme
node_ids = ["ND111", "ND222"]
node_crud.bulk_update_fields(
    session,
    node_ids,
    {
        "timeout_seconds": 600,
        "max_retries": 5
    }
)

# Bulk script parameter güncelleme
script_ids = ["SC111", "SC222"]
script_crud.bulk_update_fields(
    session,
    script_ids,
    {
        "test_status": ScriptTestStatus.PASSED,
        "input_params": {"new_param": "default_value"}
    }
)

# Hatalı alan adı
try:
    workflow_crud.bulk_update_fields(
        session,
        ["WF111"],
        {"nonexistent_field": "value"}
    )
except ValueError as e:
    print(f"Error: {e}")
```

---

## Performance Considerations

### Memory Protection
- `get_all()` ve `filter()` fonksiyonları maksimum 1000 kayıt limit'i
- `find_by_field()` maksimum 1000 kayıt limit'i
- Büyük veri setleri için pagination kullanın

### Bulk Operations
- `bulk_create()`, `bulk_update()`, `bulk_delete()` performans için optimize edilmiş
- Büyük batch'ler için chunk'lara bölün
- Transaction kullanarak atomicity sağlayın

### Index Usage
- Foreign key alanları otomatik index'lenir
- Sık kullanılan filter alanları için ek index'ler ekleyin
- Order by operations için composite index'ler kullanın

---

## Error Handling Best Practices

```python
# Transaction ile güvenli kullanım
try:
    with session.begin():
        workflow = workflow_crud.create(session, name="Test")
        node = node_crud.create(session, workflow_id=workflow.id)
        session.commit()
except Exception as e:
    session.rollback()
    logger.error(f"Transaction failed: {e}")

# Validation ile güvenli kullanım
def safe_create_workflow(name, priority):
    if workflow_crud.check_name_exists(session, name):
        raise ValueError(f"Workflow '{name}' already exists")
    
    if not 0 <= priority <= 100:
        raise ValueError("Priority must be between 0-100")
    
    return workflow_crud.create(session, name=name, priority=priority)
```

---

## Integration Examples

```python
# Entity-specific CRUD ile kullanım
class WorkflowCRUD(BaseCRUD[Workflow]):
    def __init__(self):
        super().__init__(Workflow)
    
    def set_priority(self, session, workflow_id, priority):
        # BaseCRUD'dan miras alınan metodu kullan
        return self.update(session, workflow_id, priority=priority)
    
    def get_active_workflows(self, session):
        # BaseCRUD'dan miras alınan filter metodunu kullan
        return self.filter(session, {"status": WorkflowStatus.ACTIVE})
```

This documentation provides comprehensive coverage of all BaseCRUD methods with practical examples for each function. The methods are organized by category (Basic, Query, Bulk, Optimized) to help developers understand the different types of operations available.