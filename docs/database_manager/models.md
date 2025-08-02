# Miniflow Database Manager - Models Dokümantasyonu

## Giriş

Miniflow Database Manager modülü workflow execution sisteminin tüm veri modellerini SQLAlchemy ORM ile tanımlar. Bu modeller workflow'ların tanımlanması, çalıştırılması, takip edilmesi ve arşivlenmesi için gerekli veri yapılarını oluşturur. Sistem 8 ana model ve 8 enum sınıfından oluşur ve aralarındaki ilişkiler CASCADE delete, referential integrity ve unique constraint'ler ile güçlendirilmiştir.

## Enum Sınıfları

Sistem workflow ve execution durumlarını yönetmek için 8 farklı enum sınıfı kullanır. Bu enum'lar veri tutarlılığını ve referans kontrolünü sağlar.

### WorkflowStatus

Workflow'ların yaşam döngüsündeki durumlarını tanımlar.

```python
class WorkflowStatus(str, enum.Enum):
    ACTIVE = "active"        # Aktif kullanımda olan workflow
    INACTIVE = "inactive"    # Geçici olarak devre dışı bırakılmış
    DRAFT = "draft"          # Henüz tamamlanmamış, taslak durumda
    ARCHIVED = "archived"    # Arşivlenmiş, artık kullanılmıyor
```

### ExecutionStatus

Workflow execution'larının anlık durumunu belirtir.

```python
class ExecutionStatus(str, enum.Enum):
    PENDING = "pending"      # Henüz başlatılmamış, beklemede
    RUNNING = "running"      # Şu an çalışıyor
    COMPLETED = "completed"  # Başarıyla tamamlandı
    FAILED = "failed"        # Hata ile sonlandı
    CANCELLED = "cancelled"  # İptal edildi
```

### ExecutionOutputStatus

Her node'un execution sonucunun durumunu gösterir.

```python
class ExecutionOutputStatus(str, enum.Enum):
    SUCCESS = "success"      # Node başarıyla çalıştı
    FAILURE = "failure"      # Node hata ile sonlandı
    TIMEOUT = "timeout"      # Node timeout süresini aştı
    CANCELLED = "cancelled"  # Node iptal edildi
```

### ConditionType

Edge'lerde hangi durumda bir sonraki node'a geçileceğini belirler.

```python
class ConditionType(str, enum.Enum):
    SUCCESS = "success"      # Önceki node başarılı olduğunda
    FAILURE = "failure"      # Önceki node hata verdiğinde
    ALWAYS = "always"        # Her durumda çalışır
    CONDITIONAL = "conditional"  # Özel şartlara göre
```

### ScriptType

Desteklenen script dillerini tanımlar.

```python
class ScriptType(str, enum.Enum):
    PYTHON = "python"        # Python script dosyaları
```

### ScriptTestStatus

Script'lerin test durumlarını takip eder.

```python
class ScriptTestStatus(str, enum.Enum):
    UNTESTED = "untested"    # Henüz test edilmemiş
    PASSED = "passed"        # Test başarılı
    FAILED = "failed"        # Test başarısız  
    RUNNING = "running"      # Test şu an çalışıyor
```

### AuditAction

Audit log'larda hangi işlemin gerçekleştirildiğini belirtir.

```python
class AuditAction(str, enum.Enum):
    CREATE = "CREATE"        # Yeni kayıt oluşturuldu
    UPDATE = "UPDATE"        # Mevcut kayıt güncellendi
    DELETE = "DELETE"        # Kayıt silindi
    EXECUTE = "EXECUTE"      # Workflow/Node çalıştırıldı
    ARCHIVE = "ARCHIVE"      # Kayıt arşivlendi
```

### ArchiveReason

Execution'ların neden arşivlendiğini belirtir.

```python
class ArchiveReason(str, enum.Enum):
    AUTO_CLEANUP = "auto_cleanup"        # Otomatik temizlik
    MANUAL_ARCHIVE = "manual_archive"    # Manuel arşivleme
    RETENTION_POLICY = "retention_policy" # Saklama politikası
    SYSTEM_CLEANUP = "system_cleanup"    # Sistem temizliği
```

## BaseModel Sınıfı

Tüm modellerin kalıtım aldığı temel sınıftır. Ortak özellikleri ve fonksiyonaliteyi sağlar.

```python
class BaseModel(Base):
    __prefix__ = "BM"               # Model için ID prefix'i
    __abstract__ = True             # SQLAlchemy abstract model
    __allow_unmapped__ = True       # Unmapped attribute'lere izin ver
```

### Ortak Alanlar

Her model aşağıdaki ortak alanlara sahiptir:

```python
id = Column(String(12), primary_key=True)                    # Unique identifier
created_at = Column(DateTime, default=datetime.now, nullable=False)  # Oluşturulma zamanı
updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)  # Güncellenme zamanı
```

### ID Üretimi

BaseModel otomatik ID üretimi yapar. Her model kendi prefix'ini tanımlar:

```python
@classmethod
def _generate_id(cls):
    prefix = getattr(cls, '__prefix__', 'XX')
    uuid_suffix = str(uuid.uuid4()).replace('-', '')[:10].upper()
    return f"{prefix}{uuid_suffix}"
```

**ID Format Örnekleri:**
- Workflow: `WF1A2B3C4D5E`
- Node: `ND9F8E7D6C5B`
- Script: `SC4A5B6C7D8E`

### Utility Metodları

```python
def __repr__(self) -> str:
    """Model'in string gösterimini döner"""
    return f"<{self.__class__.__name__}(id={self.id})>"

def to_dict(self) -> dict:
    """Model'i dictionary'ye çevirir, datetime ve enum değerlerini serialize eder"""
    # datetime -> ISO format
    # enum -> value
    # nested objects -> to_dict()
```

## Ana Modeller

### Workflow Modeli

Workflow'ları tanımlar ve execution süreçlerini yönetir.

```python
class Workflow(BaseModel):
    __prefix__ = "WF"
    __tablename__ = 'workflows'
    
    name = Column(String(100), nullable=False, unique=True)      # Unique workflow adı
    description = Column(Text, nullable=True)                    # Açıklama
    status = Column(Enum(WorkflowStatus), default=WorkflowStatus.DRAFT, nullable=False)  # Durum
    priority = Column(Integer, default=0, nullable=False)        # Öncelik seviyesi
```

**İlişkiler:**
- **nodes**: Workflow'a ait tüm node'lar (cascade delete)
- **edges**: Workflow'a ait tüm edge'ler (cascade delete)
- **executions**: Workflow'un execution geçmişi (cascade delete)

### Node Modeli

Workflow içindeki iş adımlarını (task'ları) temsil eder.

```python
class Node(BaseModel):
    __prefix__ = "ND"
    __tablename__ = 'nodes'
    __table_args__ = (UniqueConstraint('workflow_id', 'name', name='uq_node_workflow_name'),)
    
    workflow_id = Column(String(12), ForeignKey('workflows.id', ondelete='CASCADE'), nullable=False)
    script_id = Column(String(12), ForeignKey('scripts.id', ondelete='SET NULL'), nullable=True)
    name = Column(String(100), nullable=False)                   # Workflow içinde unique name
    params = Column(JSON, nullable=True, default=dict)          # Node parametreleri
    max_retries = Column(Integer, default=3, nullable=False)    # Maksimum tekrar sayısı
    timeout_seconds = Column(Integer, default=300, nullable=False)  # Timeout süresi (saniye)
```

**Unique Constraint**: Aynı workflow içinde node adları unique olmalıdır.

**İlişkiler:**
- **workflow**: Ait olduğu workflow (parent)
- **script**: Çalıştıracağı script (optional)
- **edges_from**: Bu node'dan çıkan edge'ler
- **edges_to**: Bu node'a gelen edge'ler
- **execution_inputs**: Execution'larda bu node için input'lar
- **execution_outputs**: Execution'larda bu node'un output'ları

### Script Modeli

Çalıştırılabilir script dosyalarını tanımlar.

```python
class Script(BaseModel):
    __prefix__ = "SC"
    __tablename__ = 'scripts'
    
    name = Column(String(100), nullable=False, unique=True)      # Global unique script adı
    description = Column(Text, nullable=True)                    # Açıklama
    language = Column(Enum(ScriptType), nullable=False, default=ScriptType.PYTHON)  # Script dili
    script_path = Column(Text, nullable=False)                   # Script dosyasının yolu
    input_params = Column(JSON, default=dict, nullable=False)   # Beklenen input parametreleri
    output_params = Column(JSON, default=dict, nullable=False)  # Üretilecek output parametreleri
    test_status = Column(Enum(ScriptTestStatus), default=ScriptTestStatus.UNTESTED, nullable=False)  # Test durumu
```

**İlişkiler:**
- **nodes**: Bu script'i kullanan node'lar

### Edge Modeli

Node'lar arası bağlantıları ve koşulları tanımlar.

```python
class Edge(BaseModel):
    __prefix__ = "ED"
    __tablename__ = 'edges'
    __table_args__ = (UniqueConstraint('workflow_id', 'from_node_id', 'to_node_id', 'condition_type', name='uq_edge_workflow_nodes_condition'),)
    
    workflow_id = Column(String(12), ForeignKey('workflows.id', ondelete='CASCADE'), nullable=False)
    from_node_id = Column(String(12), ForeignKey('nodes.id', ondelete='CASCADE'), nullable=False)
    to_node_id = Column(String(12), ForeignKey('nodes.id', ondelete='CASCADE'), nullable=False)
    condition_type = Column(Enum(ConditionType), default=ConditionType.SUCCESS, nullable=False)
```

**Unique Constraint**: Aynı workflow içinde aynı node'lar arası aynı condition type için tek edge olabilir.

**İlişkiler:**
- **workflow**: Ait olduğu workflow
- **from_node**: Kaynak node
- **to_node**: Hedef node

### Execution Modeli

Workflow'ların çalıştırılma kayıtlarını tutar.

```python
class Execution(BaseModel):
    __prefix__ = "EX"
    __tablename__ = 'executions'
    
    workflow_id = Column(String(12), ForeignKey('workflows.id', ondelete='CASCADE'), nullable=False)
    status = Column(Enum(ExecutionStatus), default=ExecutionStatus.PENDING, nullable=False)
    pending_nodes = Column(Integer, default=0, nullable=False)   # Bekleyen node sayısı
    executed_nodes = Column(Integer, default=0, nullable=False)  # Çalıştırılan node sayısı
    results = Column(JSON, default=dict, nullable=False)        # Execution sonuçları
    started_at = Column(DateTime, default=datetime.now, nullable=False)  # Başlangıç zamanı
    ended_at = Column(DateTime, nullable=True)                   # Bitiş zamanı
```

**İlişkiler:**
- **workflow**: Çalıştırılan workflow
- **execution_inputs**: Node'lar için input tanımları
- **execution_outputs**: Node'ların execution sonuçları

### ExecutionInput Modeli

Execution sırasında node'ların çalıştırılma sırasını ve bağımlılıklarını yönetir.

```python
class ExecutionInput(BaseModel):
    __prefix__ = "EI"
    __tablename__ = 'execution_inputs'
    __table_args__ = (UniqueConstraint('execution_id', 'node_id', name='uq_execution_input_execution_node'),)
    
    execution_id = Column(String(12), ForeignKey('executions.id', ondelete='CASCADE'), nullable=False)
    node_id = Column(String(12), ForeignKey('nodes.id', ondelete='CASCADE'), nullable=False)
    priority = Column(Integer, default=0, nullable=False)       # Çalıştırma önceliği
    dependency_count = Column(Integer, default=0, nullable=False)  # Bağımlılık sayısı
    wait_factor = Column(Integer, default=0, nullable=False)    # Bekleme faktörü
```

**Unique Constraint**: Her execution'da her node için tek ExecutionInput olabilir.

**İlişkiler:**
- **execution**: Ait olduğu execution
- **node**: İlgili node

### ExecutionOutput Modeli

Node'ların execution sonuçlarını detaylı olarak saklar.

```python
class ExecutionOutput(BaseModel):
    __prefix__ = "EO"
    __tablename__ = 'execution_outputs'
    __table_args__ = (UniqueConstraint('execution_id', 'node_id', name='uq_execution_output_execution_node'),)
    
    execution_id = Column(String(12), ForeignKey('executions.id', ondelete='CASCADE'), nullable=False)
    node_id = Column(String(12), ForeignKey('nodes.id', ondelete='CASCADE'), nullable=False)
    status = Column(Enum(ExecutionOutputStatus), nullable=False)  # Node'un execution durumu
    result_data = Column(JSON, nullable=True)                    # Node'un ürettiği sonuç verisi
    started_at = Column(DateTime, nullable=True)                 # Node başlangıç zamanı
    ended_at = Column(DateTime, nullable=True)                   # Node bitiş zamanı
```

**Unique Constraint**: Her execution'da her node için tek ExecutionOutput olabilir.

**İlişkiler:**
- **execution**: Ait olduğu execution
- **node**: İlgili node

### ArchivedExecution Modeli

Tamamlanmış execution'ların arşiv kopyalarını saklar.

```python
class ArchivedExecution(BaseModel):
    __prefix__ = "AE"
    __tablename__ = 'archived_executions'
    
    original_execution_id = Column(String(12), unique=True, nullable=False)  # Orijinal execution ID'si
    workflow_id = Column(String(12), ForeignKey('workflows.id'), nullable=False)
    status = Column(Enum(ExecutionStatus), nullable=False)      # Final execution durumu
    success = Column(Boolean, default=False, nullable=False)    # Başarılı mı?
    results = Column(JSON, default=dict, nullable=False)       # Execution sonuçları
    started_at = Column(DateTime, nullable=False)               # Başlangıç zamanı
    ended_at = Column(DateTime, nullable=True)                  # Bitiş zamanı
    archived_at = Column(DateTime, default=datetime.now, nullable=False)  # Arşivlenme zamanı
    archive_reason = Column(Enum(ArchiveReason), default=ArchiveReason.AUTO_CLEANUP, nullable=False)  # Arşivleme sebebi
```

**İlişkiler:**
- **workflow**: İlgili workflow (sadece referans, cascade yok)

### AuditLog Modeli

Sistem üzerindeki tüm önemli işlemleri kaydeder.

```python
class AuditLog(BaseModel):
    __prefix__ = "AL"
    __tablename__ = 'audit_logs'
    
    table_name = Column(String(100), nullable=False)            # Hangi tabloda işlem yapıldı
    record_id = Column(String(12), nullable=False)              # Hangi kayıtta işlem yapıldı
    action = Column(Enum(AuditAction), nullable=False)          # Hangi işlem yapıldı
    old_values = Column(JSON, nullable=True)                    # Eski değerler (UPDATE/DELETE için)
    new_values = Column(JSON, nullable=True)                    # Yeni değerler (CREATE/UPDATE için)
```

**İlişki yok**: AuditLog bağımsız bir kayıt sistemidir.

### EnvironmentVariable Modeli

Environment variable'ları ve sistem konfigrasyonlarını tutar.

```python
class EnvironmentVariable(BaseModel):
    __prefix__ = "EV"
    __tablename__ = 'environment_variables'
    
    name = Column(String(100), nullable=False, unique=True)         # Environment variable adı (unique)
    value = Column(String(255), nullable=False)                     # Variable değeri
    description = Column(Text, nullable=True)                       # Açıklama
    is_sensitive = Column(Boolean, default=False, nullable=False)   # Gizli bilgi mi?
```

**Özellikleri:**
- **name**: Environment variable adı (örn: "DATABASE_URL", "API_KEY")
- **value**: Variable değeri (hassas bilgiler için şifrelenebilir)
- **description**: Variable'ın ne için kullanıldığının açıklaması
- **is_sensitive**: True ise log'larda ve export'larda maskelenecek

**İlişki yok**: EnvironmentVariable bağımsız bir konfigrasyon sistemidir.

**Kullanım Senaryoları:**
```python
# API key tanımlama
api_key = EnvironmentVariable(
    name="OPENAI_API_KEY",
    value="sk-...",
    description="OpenAI API anahtarı",
    is_sensitive=True
)

# Database URL tanımlama  
db_url = EnvironmentVariable(
    name="DATABASE_URL", 
    value="postgresql://user:pass@localhost/db",
    description="Ana veritabanı bağlantı string'i",
    is_sensitive=True
)

# Sistem ayarı
debug_mode = EnvironmentVariable(
    name="DEBUG_MODE",
    value="false", 
    description="Hata ayıklama modu aktif mi?",
    is_sensitive=False
)
```

## Model İlişkileri ve Cascade Davranışları

### Workflow ↔ Node İlişkisi
- **İlişki**: One-to-Many (Workflow → Node)
- **Cascade**: `all, delete-orphan`
- **Davranış**: Workflow silindiğinde tüm node'ları da silinir

### Workflow ↔ Execution İlişkisi
- **İlişki**: One-to-Many (Workflow → Execution)
- **Cascade**: `all, delete-orphan`
- **Davranış**: Workflow silindiğinde tüm execution'ları da silinir

### Node ↔ Script İlişkisi
- **İlişki**: Many-to-One (Node → Script)
- **Cascade**: `SET NULL`
- **Davranış**: Script silindiğinde node'ların script_id'si NULL olur

### Node ↔ Edge İlişkisi
- **İlişki**: One-to-Many (Node → Edge, iki yönlü)
- **Cascade**: `all, delete-orphan`
- **Davranış**: Node silindiğinde bu node'u kullanan tüm edge'ler silinir

### Execution ↔ ExecutionInput/Output İlişkisi
- **İlişki**: One-to-Many (Execution → ExecutionInput/Output)
- **Cascade**: `all, delete-orphan`
- **Davranış**: Execution silindiğinde tüm input/output kayıtları silinir

## Unique Constraint'ler

### Node Model
```sql
CONSTRAINT uq_node_workflow_name UNIQUE (workflow_id, name)
```
Aynı workflow içinde node adları benzersiz olmalıdır.

### Edge Model
```sql
CONSTRAINT uq_edge_workflow_nodes_condition UNIQUE (workflow_id, from_node_id, to_node_id, condition_type)
```
Aynı workflow içinde aynı node'lar arası aynı condition için tek edge olabilir.

### ExecutionInput Model
```sql
CONSTRAINT uq_execution_input_execution_node UNIQUE (execution_id, node_id)
```
Her execution'da her node için tek input kaydı olabilir.

### ExecutionOutput Model
```sql
CONSTRAINT uq_execution_output_execution_node UNIQUE (execution_id, node_id)
```
Her execution'da her node için tek output kaydı olabilir.

## Kullanım Senaryoları

### Workflow Oluşturma
```python
from miniflow.database_manager.models import Workflow, Node, Script, Edge

# 1. Workflow oluştur
workflow = Workflow(
    name="Data Processing Pipeline",
    description="ETL pipeline for customer data",
    status=WorkflowStatus.DRAFT
)

# 2. Script'leri tanımla
extract_script = Script(
    name="extract_customer_data",
    language=ScriptType.PYTHON,
    script_path="/scripts/extract.py",
    input_params={"source": "database"},
    output_params={"customers": "list"}
)

# 3. Node'ları oluştur
extract_node = Node(
    workflow=workflow,
    script=extract_script,
    name="Extract Data",
    timeout_seconds=600
)

transform_node = Node(
    workflow=workflow,
    name="Transform Data",
    timeout_seconds=300
)

# 4. Edge ile bağla
edge = Edge(
    workflow=workflow,
    from_node=extract_node,
    to_node=transform_node,
    condition_type=ConditionType.SUCCESS
)
```

### Execution Takibi
```python
from miniflow.database_manager.models import Execution, ExecutionInput, ExecutionOutput

# Execution başlat
execution = Execution(
    workflow=workflow,
    status=ExecutionStatus.PENDING,
    pending_nodes=2,
    executed_nodes=0
)

# Node execution sonucunu kaydet
output = ExecutionOutput(
    execution=execution,
    node=extract_node,
    status=ExecutionOutputStatus.SUCCESS,
    result_data={"customer_count": 1500},
    started_at=datetime.now(),
    ended_at=datetime.now()
)
```

### Audit Logging
```python
from miniflow.database_manager.models import AuditLog

# Workflow oluşturma işlemini logla
audit = AuditLog(
    table_name="workflows",
    record_id=workflow.id,
    action=AuditAction.CREATE,
    new_values=workflow.to_dict()
)
```

### Environment Variable Yönetimi
```python
from miniflow.database_manager.models import EnvironmentVariable

# Sistem konfigrasyonu oluştur
config_vars = [
    EnvironmentVariable(
        name="MAX_WORKERS",
        value="10",
        description="Maksimum worker thread sayısı"
    ),
    EnvironmentVariable(
        name="SECRET_KEY",
        value="super-secret-key-123",
        description="JWT token için gizli anahtar",
        is_sensitive=True
    ),
    EnvironmentVariable(
        name="LOG_LEVEL", 
        value="INFO",
        description="Sistem log seviyesi"
    )
]

# Session ile kaydet
for var in config_vars:
    session.add(var)
```

## Kısacası

Models modülü miniflow'un kalbi olan veri yapılarını tanımlar. 9 model sınıfı workflow'ların tanımlanması, çalıştırılması, takip edilmesi ve sistem konfigrasyonu için gereken tüm veri yapılarını kapsar. Enum'lar veri tutarlılığını, foreign key'ler referential integrity'yi, unique constraint'ler iş kurallarını sağlar. CASCADE delete'ler veri bütünlüğünü korurken, JSON alanlar esnek parametre yönetimi sunar. BaseModel tüm modellere ortak fonksiyonalite kazandırır ve ID üretimi, timestamp'ler, serialization gibi temel ihtiyaçları karşılar. EnvironmentVariable modeli sistem konfigrasyonlarının güvenli yönetimini sağlar.