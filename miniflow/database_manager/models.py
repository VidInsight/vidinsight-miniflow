"""
DATABASE MODELS MODULE
======================

Bu modül Miniflow sisteminin tüm SQLAlchemy ORM model tanımlarını içerir.
Database schema'nın kalbi olan bu modül, workflow orchestration için
gerekli tüm entity'leri ve ilişkileri tanımlar.

MODÜL SORUMLULUKLARI:
====================
1. Entity Definitions - Workflow, Node, Execution vb. core entity'ler
2. Relationship Mapping - Entity'ler arası ilişki tanımları
3. Enum Definitions - Status ve type enum'ları
4. Database Indexes - Performance optimization için index tanımları
5. Validation Logic - Model-level veri doğrulama kuralları

DATABASE SCHEMA OVERVIEW:
========================
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Workflows  │────│    Nodes    │────│   Scripts   │
│             │    │             │    │             │
│ • Name      │    │ • Name      │    │ • Code      │
│ • Status    │    │ • Params    │    │ • Language  │
│ • Priority  │    │ • Retries   │    │ • Path      │
└─────────────┘    └─────────────┘    └─────────────┘
       │                   │                   
       │            ┌─────────────┐            
       │            │    Edges    │            
       │            │             │            
       │            │ • From Node │            
       │            │ • To Node   │            
       │            │ • Condition │            
       │            └─────────────┘            
       │                                      
       │            ┌─────────────┐    ┌─────────────┐
       └────────────│ Executions  │────│  Outputs    │
                    │             │    │             │
                    │ • Status    │    │ • Results   │
                    │ • Progress  │    │ • Timing    │
                    │ • Results   │    │ • Status    │
                    └─────────────┘    └─────────────┘

MODEL INHERITANCE HIERARCHY:
===========================
BaseModel (Abstract)
├── Workflow
├── Node  
├── Edge
├── Script
├── Execution
├── ExecutionInput
├── ExecutionOutput
├── ArchivedExecution
├── Trigger
└── AuditLog

ENUM CATEGORIES:
===============
• Workflow States: ACTIVE, INACTIVE, DRAFT, ARCHIVED
• Execution States: PENDING, RUNNING, COMPLETED, FAILED, CANCELLED
• Output States: SUCCESS, FAILURE, TIMEOUT, CANCELLED
• Trigger Types: MANUAL, SCHEDULE, WEBHOOK, FILE_WATCH, API
• Script Types: PYTHON (extensible)
• Audit Actions: CREATE, UPDATE, DELETE, EXECUTE, ARCHIVE
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, JSON, Float, Boolean, Enum, UniqueConstraint
from sqlalchemy.orm import declarative_base, relationship
from typing import Optional, List
from datetime import datetime
import uuid
import enum

# =============================================================================
# ENUM DEFINITIONS
# Database modellerinde kullanılan enum türleri
# =============================================================================

class WorkflowStatus(str, enum.Enum):
    """
    Workflow durumu enum'u
    
    Workflow yaşam döngüsünü temsil eder:
    • DRAFT: Geliştirme aşamasında, henüz aktif değil
    • ACTIVE: Prodüksiyon ortamında aktif, trigger'lanabilir
    • INACTIVE: Geçici olarak devre dışı, maintenance için
    • ARCHIVED: Kalıcı olarak arşivlenmiş, silinmeye hazır
    """
    ACTIVE = "active"         # Production'da aktif workflow
    INACTIVE = "inactive"     # Geçici olarak devre dışı
    DRAFT = "draft"           # Geliştirme aşamasında
    ARCHIVED = "archived"     # Arşivlenmiş, kullanım dışı

class ExecutionStatus(str, enum.Enum):
    """
    Execution durumu enum'u
    
    Workflow execution'ının gerçek zamanlı durumunu temsil eder:
    • PENDING: Başlatılmayı bekliyor, queue'da
    • RUNNING: Aktif olarak çalışıyor, node'lar işleniyor
    • COMPLETED: Başarıyla tamamlandı, tüm node'lar bitti
    • FAILED: Hata nedeniyle başarısız oldu
    • CANCELLED: Kullanıcı veya sistem tarafından iptal edildi
    """
    PENDING = "pending"       # Execution queue'da bekliyor
    RUNNING = "running"       # Aktif olarak çalışıyor
    COMPLETED = "completed"   # Başarıyla tamamlandı
    FAILED = "failed"         # Hata nedeniyle başarısız
    CANCELLED = "cancelled"   # İptal edildi

class ExecutionOutputStatus(str, enum.Enum):
    """
    Node execution sonucu enum'u
    
    Her node'un individual execution sonucunu temsil eder:
    • SUCCESS: Node başarıyla tamamlandı
    • FAILURE: Node hata verdi veya exception fırlattı
    • TIMEOUT: Node belirlenen sürede tamamlanamadı
    • CANCELLED: Node execution iptal edildi
    """
    SUCCESS = "success"       # Node başarıyla tamamlandı
    FAILURE = "failure"       # Node execution başarısız
    TIMEOUT = "timeout"       # Timeout nedeniyle başarısız
    CANCELLED = "cancelled"   # İptal edildi

class ConditionType(str, enum.Enum):
    """
    Edge condition türü enum'u
    
    Node'lar arası geçiş koşullarını tanımlar:
    • SUCCESS: Sadece başarılı execution sonrası geçiş
    • FAILURE: Sadece başarısız execution sonrası geçiş  
    • ALWAYS: Sonuç ne olursa olsun geçiş
    • CONDITIONAL: Özel koşul mantığı (gelecekte implement edilecek)
    """
    SUCCESS = "success"       # Başarı durumunda geçiş
    FAILURE = "failure"       # Başarısızlık durumunda geçiş
    ALWAYS = "always"         # Her durumda geçiş
    CONDITIONAL = "conditional"  # Özel koşul mantığı

class TriggerType(str, enum.Enum):
    """
    Workflow tetikleme türü enum'u
    
    Workflow'un nasıl başlatılacağını tanımlar:
    • MANUAL: Manuel tetikleme (API/UI)
    • SCHEDULE: Zamanlı tetikleme (cron-like)
    • WEBHOOK: HTTP webhook ile tetikleme
    • FILE_WATCH: Dosya değişikliği ile tetikleme
    • API: REST API call ile tetikleme
    """
    MANUAL = "manual"         # Manuel başlatma
    SCHEDULE = "schedule"     # Zamanlanmış başlatma
    WEBHOOK = "webhook"       # Webhook ile başlatma
    FILE_WATCH = "file_watch" # Dosya izleme ile başlatma
    API = "api"               # API call ile başlatma

class ScriptType(str, enum.Enum):
    """
    Script dili türü enum'u
    
    Desteklenen script dillerini tanımlar.
    Şu anda sadece Python destekleniyor, gelecekte genişletilebilir.
    """
    PYTHON = "python"         # Python script'i

class TestStatus(str, enum.Enum):
    """
    Script test durumu enum'u
    
    Script'in test edilme durumunu takip eder:
    • UNTESTED: Henüz test edilmemiş
    • PASSED: Test başarılı
    • FAILED: Test başarısız
    • RUNNING: Test şu anda çalışıyor
    """
    UNTESTED = "untested"     # Test edilmemiş
    PASSED = "passed"         # Test başarılı
    FAILED = "failed"         # Test başarısız
    RUNNING = "running"       # Test çalışıyor

class AuditAction(str, enum.Enum):
    """
    Audit log aksiyon türü enum'u
    
    Sistem üzerinde yapılan işlemleri kategorize eder:
    • CREATE: Yeni kayıt oluşturma
    • UPDATE: Mevcut kayıt güncelleme
    • DELETE: Kayıt silme
    • EXECUTE: Workflow/script çalıştırma
    • ARCHIVE: Kayıt arşivleme
    """
    CREATE = "CREATE"         # Kayıt oluşturma
    UPDATE = "UPDATE"         # Kayıt güncelleme
    DELETE = "DELETE"         # Kayıt silme
    EXECUTE = "EXECUTE"       # Execution başlatma
    ARCHIVE = "ARCHIVE"       # Arşivleme

class ArchiveReason(str, enum.Enum):
    """
    Arşivleme sebep türü enum'u
    
    Execution'ların neden arşivlendiğini takip eder:
    • AUTO_CLEANUP: Otomatik temizlik işlemi
    • MANUAL_ARCHIVE: Manuel arşivleme
    • RETENTION_POLICY: Veri saklama politikası
    • SYSTEM_CLEANUP: Sistem bakım temizliği
    """
    AUTO_CLEANUP = "auto_cleanup"         # Otomatik temizlik
    MANUAL_ARCHIVE = "manual_archive"     # Manuel arşivleme  
    RETENTION_POLICY = "retention_policy" # Veri saklama politikası
    SYSTEM_CLEANUP = "system_cleanup"     # Sistem temizliği

# =============================================================================
# BASE MODEL DEFINITIONS
# Tüm model'lar için ortak base class tanımları
# =============================================================================

# SQLAlchemy declarative base
Base = declarative_base()

class BaseModel(Base):
    """
    Tüm database model'ları için ortak base sınıf
    
    Bu abstract base class tüm model'lara ortak functionality sağlar:
    • UUID-based primary key (unique across distributed systems)
    • Automatic timestamp tracking (created_at, updated_at)
    • Dictionary serialization (API responses için)
    • Consistent string representation (debugging için)
    
    COMMON FIELDS:
    ==============
    • id: UUID primary key (string format, 36 karakter)
    • created_at: Kayıt oluşturma zamanı (otomatik)
    • updated_at: Son güncelleme zamanı (otomatik)
    
    COMMON METHODS:
    ===============
    • to_dict(): Model'i dictionary'ye çevirme
    • __repr__(): Debug string representation
    
    UUID FORMAT:
    ============
    UUID'ler string olarak saklanır (36 karakter):
    Örnek: "550e8400-e29b-41d4-a716-446655440000"
    
    BENEFITS:
    =========
    • Distributed system compatibility
    • No auto-increment collision risk
    • URL-safe identifier format
    • Database vendor independence
    """
    __abstract__ = True                     # Bu sınıf direkt table oluşturmaz
    __allow_unmapped__ = True               # Legacy annotation desteği
    
    # Primary key - UUID format (distributed systems için ideal)
    id = Column(
        String(36),                         # UUID string formatı (36 karakter)
        primary_key=True,                   # Primary key constraint
        default=lambda: str(uuid.uuid4())   # Otomatik UUID generation
    )
    
    # Automatic timestamp tracking
    created_at = Column(
        DateTime,                           # Timestamp türü
        default=datetime.utcnow,            # Oluşturma anında otomatik set
        nullable=False                      # Null olamaz
    )
    
    updated_at = Column(
        DateTime,                           # Timestamp türü
        default=datetime.utcnow,            # İlk oluşturmada otomatik set
        onupdate=datetime.utcnow,           # Her update'de otomatik güncelleme
        nullable=False                      # Null olamaz
    )
    
    def to_dict(self) -> dict:
        """
        Model instance'ını dictionary formatına çevirir
        
        Bu method model'ları JSON API response'larında kullanmak için
        dictionary formatına serialize eder. Özel type'lar için
        conversion logic içerir.
        
        CONVERSION RULES:
        =================
        • datetime objects → ISO format string
        • enum objects → value property
        • nested objects → recursive to_dict() call
        • primitive types → as-is
        
        Returns:
            dict: Model'in dictionary representation'ı
            
        Example:
            >>> workflow = Workflow(name="test", status=WorkflowStatus.ACTIVE)
            >>> result = workflow.to_dict()
            >>> print(result['status'])  # "active"
        """
        result = {}
        
        # Her column için value'yu extract et ve type conversion yap
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            
            # Type-specific conversion logic
            if isinstance(value, datetime):
                value = value.isoformat()           # ISO 8601 format
            elif isinstance(value, enum.Enum):
                value = value.value                 # Enum'un string value'su
            elif hasattr(value, 'to_dict'):
                value = value.to_dict()             # Nested object support
            # Primitive types (int, str, bool) olduğu gibi kalır
            
            result[column.name] = value
            
        return result
    
    def __repr__(self) -> str:
        """
        Model'in string representation'ı
        
        Debug ve logging amaçlı readable string representation döndürür.
        Class adı ve ID'yi içerir.
        
        Returns:
            str: Model'in string representation'ı
            
        Example:
            >>> workflow = Workflow(name="test")
            >>> print(workflow)  # <Workflow(id=550e8400-e29b...)>
        """
        return f"<{self.__class__.__name__}(id={self.id})>"

# =============================================================================
# CORE WORKFLOW MODELS
# Workflow orchestration için ana entity tanımları
# =============================================================================

class Workflow(BaseModel):
    """
    Workflow modeli - İş akışı tanımlarını temsil eder
    
    Workflow, bir dizi Node'un belirli kurallara göre çalışması için
    organize edilmiş yapıdır. Her workflow unique bir name'e sahiptir
    ve lifecycle boyunca farklı status'lerde bulunabilir.
    
    WORKFLOW LIFECYCLE:
    ==================
    DRAFT → ACTIVE → INACTIVE → ARCHIVED
    
    FIELDS:
    =======
    • name: Unique workflow identifier (URL slug olarak kullanılabilir)
    • description: Human-readable workflow açıklaması
    • status: Workflow'un current state'i (enum)
    • priority: Execution priority (higher number = higher priority)
    
    RELATIONSHIPS:
    ==============
    • nodes: Workflow'a ait node'lar (1:N)
    • edges: Node'lar arası connection'lar (1:N)
    • executions: Workflow çalıştırma kayıtları (1:N)
    • triggers: Workflow tetikleme kuralları (1:N)
    
    CONSTRAINTS:
    ============
    • name: UNIQUE (system-wide unique workflow names)
    • status: NOT NULL (her workflow'un bir durumu olmalı)
    • priority: NOT NULL, DEFAULT 0 (normal priority)
    
    CASCADING DELETES:
    ==================
    Workflow silindiğinde tüm bağlı entity'ler de silinir:
    - Nodes (and their execution history)
    - Edges (workflow connections)
    - Executions (runtime history)
    - Triggers (activation rules)
    """
    __tablename__ = 'workflows'

    # Business fields
    name = Column(
        String(255),                        # Workflow unique name
        nullable=False,                     # Required field
        unique=True                         # System-wide unique constraint
    )
    
    description = Column(
        Text,                               # Long text description
        nullable=True                       # Optional field
    )
    
    status = Column(
        Enum(WorkflowStatus),               # Status enum type
        default=WorkflowStatus.DRAFT,       # Default: development mode
        nullable=False                      # Required field
    )
    
    priority = Column(
        Integer,                            # Priority level
        default=0,                          # Normal priority as default
        nullable=False                      # Required field
    )

    # Relationships - One-to-Many relationships with cascade delete
    nodes: List["Node"] = relationship(
        "Node",                             # Target model
        back_populates="workflow",          # Bidirectional relationship
        cascade="all, delete-orphan"        # Delete nodes when workflow deleted
    )
    
    edges: List["Edge"] = relationship(
        "Edge",                             # Target model
        back_populates="workflow",          # Bidirectional relationship
        cascade="all, delete-orphan"        # Delete edges when workflow deleted
    )
    
    executions: List["Execution"] = relationship(
        "Execution",                        # Target model
        back_populates="workflow",          # Bidirectional relationship
        cascade="all, delete-orphan"        # Delete executions when workflow deleted
    )
    
    triggers: List["Trigger"] = relationship(
        "Trigger",                          # Target model
        back_populates="workflow",          # Bidirectional relationship
        cascade="all, delete-orphan"        # Delete triggers when workflow deleted
    )

# Nodes Table
class Node(BaseModel):
    """
    Node modeli - İş akışı düğümlerini temsil eder
    """
    __tablename__ = 'nodes'
    __table_args__ = (UniqueConstraint('workflow_id', 'name', name='uq_node_workflow_name'),)

    workflow_id = Column(String(36), ForeignKey('workflows.id', ondelete='CASCADE'), nullable=False)
    script_id = Column(String(36), ForeignKey('scripts.id', ondelete='SET NULL'), nullable=True)
    name = Column(String(255), nullable=False) 
    params = Column(JSON, nullable=True, default=lambda: {})
    max_retries = Column(Integer, default=3, nullable=False)
    timeout_seconds = Column(Integer, default=300, nullable=False)

    # Relationships
    workflow: "Workflow" = relationship("Workflow", back_populates="nodes")
    script: Optional["Script"] = relationship("Script", back_populates="nodes")
    edges_from: List["Edge"] = relationship("Edge", foreign_keys="[Edge.from_node_id]", back_populates="from_node", cascade="all, delete-orphan")
    edges_to: List["Edge"] = relationship("Edge", foreign_keys="[Edge.to_node_id]", back_populates="to_node", cascade="all, delete-orphan")
    execution_inputs: List["ExecutionInput"] = relationship("ExecutionInput", back_populates="node", cascade="all, delete-orphan")
    execution_outputs: List["ExecutionOutput"] = relationship("ExecutionOutput", back_populates="node", cascade="all, delete-orphan")

# Edges Table
class Edge(BaseModel):
    """
    Edge modeli - Düğümler arası bağlantıları temsil eder
    """
    __tablename__ = 'edges'
    __table_args__ = (UniqueConstraint('workflow_id', 'from_node_id', 'to_node_id', 'condition_type', name='uq_edge_workflow_nodes_condition'),)

    workflow_id = Column(String(36), ForeignKey('workflows.id', ondelete='CASCADE'), nullable=False)
    from_node_id = Column(String(36), ForeignKey('nodes.id', ondelete='CASCADE'), nullable=False)
    to_node_id = Column(String(36), ForeignKey('nodes.id', ondelete='CASCADE'), nullable=False)
    condition_type = Column(Enum(ConditionType), default=ConditionType.SUCCESS, nullable=False)

    # Relationships
    workflow: "Workflow" = relationship("Workflow", back_populates="edges")
    from_node: "Node" = relationship("Node", foreign_keys=[from_node_id], back_populates="edges_from")
    to_node: "Node" = relationship("Node", foreign_keys=[to_node_id], back_populates="edges_to")

# Triggers Table
class Trigger(BaseModel):
    """
    Trigger modeli - İş akışı tetikleyicilerini temsil eder
    """
    __tablename__ = 'triggers'
    
    workflow_id = Column(String(36), ForeignKey('workflows.id', ondelete='CASCADE'), nullable=False)
    trigger_type = Column(Enum(TriggerType), nullable=False)
    trigger_config = Column(JSON, default=lambda: {}, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    workflow: "Workflow" = relationship("Workflow", back_populates="triggers")

# Scripts Table 
class Script(BaseModel):
    """
    Script modeli - Yeniden kullanılabilir script tanımları
    """
    __tablename__ = 'scripts'

    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    language = Column(Enum(ScriptType), nullable=False, default=ScriptType.PYTHON) 
    script_path = Column(Text, nullable=False)
    input_params = Column(JSON, default=lambda: {}, nullable=False)
    output_params = Column(JSON, default=lambda: {}, nullable=False)
    test_status = Column(Enum(TestStatus), default=TestStatus.UNTESTED, nullable=False)

    # Relationships
    nodes: List["Node"] = relationship("Node", back_populates="script")

# Executions Table
class Execution(BaseModel):
    """
    Execution modeli - İş akışı çalıştırmalarını temsil eder
    """
    __tablename__ = 'executions'

    workflow_id = Column(String(36), ForeignKey('workflows.id', ondelete='CASCADE'), nullable=False)
    status = Column(Enum(ExecutionStatus), default=ExecutionStatus.PENDING, nullable=False)
    pending_nodes = Column(Integer, default=0, nullable=False)  
    executed_nodes = Column(Integer, default=0, nullable=False) 
    results = Column(JSON, default=lambda: {}, nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    ended_at = Column(DateTime, nullable=True)

    # Relationships
    workflow: "Workflow" = relationship("Workflow", back_populates="executions")
    execution_inputs: List["ExecutionInput"] = relationship("ExecutionInput", back_populates="execution", cascade="all, delete-orphan")
    execution_outputs: List["ExecutionOutput"] = relationship("ExecutionOutput", back_populates="execution", cascade="all, delete-orphan")

# Execution Inputs Table 
class ExecutionInput(BaseModel):
    """
    ExecutionInput modeli - Çalıştırma kuyruğunu temsil eder
    """
    __tablename__ = 'execution_inputs'
    __table_args__ = (UniqueConstraint('execution_id', 'node_id', name='uq_execution_input_execution_node'),)
    
    execution_id = Column(String(36), ForeignKey('executions.id', ondelete='CASCADE'), nullable=False)
    node_id = Column(String(36), ForeignKey('nodes.id', ondelete='CASCADE'), nullable=False)
    priority = Column(Integer, default=0, nullable=False)
    dependency_count = Column(Integer, default=0, nullable=False)
    wait_factor = Column(Integer, default=0, nullable=False)

    # Relationships
    execution: "Execution" = relationship("Execution", back_populates="execution_inputs")
    node: "Node" = relationship("Node", back_populates="execution_inputs")

# Execution Outputs Table
class ExecutionOutput(BaseModel):
    """
    ExecutionOutput modeli - Çalıştırma sonuçlarını temsil eder
    """
    __tablename__ = 'execution_outputs'
    __table_args__ = (UniqueConstraint('execution_id', 'node_id', name='uq_execution_output_execution_node'),)
    
    execution_id = Column(String(36), ForeignKey('executions.id', ondelete='CASCADE'), nullable=False)
    node_id = Column(String(36), ForeignKey('nodes.id', ondelete='CASCADE'), nullable=False)
    status = Column(Enum(ExecutionOutputStatus), nullable=False)
    result_data = Column(JSON, nullable=True)
    started_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)

    # Relationships
    execution: "Execution" = relationship("Execution", back_populates="execution_outputs")
    node: "Node" = relationship("Node", back_populates="execution_outputs")

# Archived Executions Table
class ArchivedExecution(BaseModel):
    """
    ArchivedExecution modeli - Eski execution kayıtları
    """
    __tablename__ = 'archived_executions'

    original_execution_id = Column(String(36), unique=True, nullable=False)
    workflow_id = Column(String(36), nullable=False)  # FK yok - workflow silinmiş olabilir
    status = Column(Enum(ExecutionStatus), nullable=False)
    success = Column(Boolean, default=False, nullable=False)
    results = Column(JSON, default=lambda: {}, nullable=False)
    started_at = Column(DateTime, nullable=False)
    ended_at = Column(DateTime, nullable=True)
    archived_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    archive_reason = Column(Enum(ArchiveReason), default=ArchiveReason.AUTO_CLEANUP, nullable=False)

# Audit Log Table
class AuditLog(BaseModel):
    """
    AuditLog modeli - Sistem değişikliklerinin izlenmesi
    """
    __tablename__ = 'audit_logs'
    
    table_name = Column(String(100), nullable=False)
    record_id = Column(String(36), nullable=False)  # UUID ile uyumlu hale getirildi
    action = Column(Enum(AuditAction), nullable=False)
    old_values = Column(JSON, nullable=True)
    new_values = Column(JSON, nullable=True)
    user_id = Column(String(100), nullable=True)
    ip_address = Column(String(45), nullable=True)  # IPv6 için 45 karakter
    user_agent = Column(String(500), nullable=True)


# VERITABANI INDEKSLERI
# ==============================================================
INDEXES = [
     # FK indeksleri (mecburi)
    "CREATE INDEX IF NOT EXISTS idx_nodes_workflow_id ON nodes(workflow_id)",
    "CREATE INDEX IF NOT EXISTS idx_edges_workflow_id ON edges(workflow_id)", 
    "CREATE INDEX IF NOT EXISTS idx_edges_from_node ON edges(from_node_id)",
    "CREATE INDEX IF NOT EXISTS idx_edges_to_node ON edges(to_node_id)",
    "CREATE INDEX IF NOT EXISTS idx_executions_workflow_id ON executions(workflow_id)",
    "CREATE INDEX IF NOT EXISTS idx_execution_inputs_execution_id ON execution_inputs(execution_id)",
    "CREATE INDEX IF NOT EXISTS idx_execution_outputs_execution_id ON execution_outputs(execution_id)",
    
    # Temel sorgular
    "CREATE INDEX IF NOT EXISTS idx_workflows_status ON workflows(status)",
    "CREATE INDEX IF NOT EXISTS idx_executions_status ON executions(status)",
    "CREATE INDEX IF NOT EXISTS idx_executions_started_at ON executions(started_at DESC)",
    
    # Composite (en önemliler)
    "CREATE INDEX IF NOT EXISTS idx_executions_workflow_status ON executions(workflow_id, status)",
    
    # SCHEDULER PERFORMANCE INDEXES
    # ==============================================================
    # Ready tasks query optimization
    "CREATE INDEX IF NOT EXISTS idx_execution_inputs_dependency_count ON execution_inputs(dependency_count)",
    "CREATE INDEX IF NOT EXISTS idx_execution_inputs_ready_tasks ON execution_inputs(dependency_count, priority DESC, created_at)",
    
    # Node dependency resolution
    "CREATE INDEX IF NOT EXISTS idx_edges_dependency_lookup ON edges(from_node_id, to_node_id, condition_type)",
    "CREATE INDEX IF NOT EXISTS idx_execution_inputs_node_execution ON execution_inputs(node_id, execution_id)",
    
    # Output processing optimization
    "CREATE INDEX IF NOT EXISTS idx_execution_outputs_node_execution ON execution_outputs(execution_id, node_id)",
    "CREATE INDEX IF NOT EXISTS idx_execution_outputs_status ON execution_outputs(status)",
    "CREATE INDEX IF NOT EXISTS idx_execution_outputs_execution_status ON execution_outputs(execution_id, status)",
    
    # Dynamic parameter resolution
    "CREATE INDEX IF NOT EXISTS idx_nodes_name_workflow ON nodes(name, workflow_id)",
    "CREATE INDEX IF NOT EXISTS idx_execution_outputs_node_name_lookup ON execution_outputs(execution_id, node_id, status)",
    
    # Execution progress tracking
    "CREATE INDEX IF NOT EXISTS idx_executions_pending_nodes ON executions(pending_nodes)",
    "CREATE INDEX IF NOT EXISTS idx_executions_status_progress ON executions(status, pending_nodes, executed_nodes)",
    
    # Script lookups for payload creation
    "CREATE INDEX IF NOT EXISTS idx_nodes_script_id ON nodes(script_id)",
    "CREATE INDEX IF NOT EXISTS idx_scripts_path ON scripts(script_path)",
]