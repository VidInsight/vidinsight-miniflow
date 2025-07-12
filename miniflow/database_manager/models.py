"""
DatabaseManager tarafında kullanılacak olan model tanımları
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, JSON, Float, Boolean, Enum, UniqueConstraint
from sqlalchemy.orm import declarative_base, relationship
from typing import Optional, List
from datetime import datetime
import uuid
import enum


# VERITABANI MODELLERINDE KULLANILACAK ENUM TANIMLARI
# ==============================================================

class WorkflowStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    DRAFT = "draft"
    ARCHIVED = "archived"

class ExecutionStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class ExecutionOutputStatus(str, enum.Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"

class ConditionType(str, enum.Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    ALWAYS = "always"
    CONDITIONAL = "conditional"

class TriggerType(str, enum.Enum):
    MANUAL = "manual"
    SCHEDULE = "schedule"
    WEBHOOK = "webhook"
    FILE_WATCH = "file_watch"
    API = "api"

class ScriptType(str, enum.Enum):
    PYTHON = "python"

class TestStatus(str, enum.Enum):
    UNTESTED = "untested"
    PASSED = "passed"
    FAILED = "failed"
    RUNNING = "running"

class AuditAction(str, enum.Enum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    EXECUTE = "EXECUTE"
    ARCHIVE = "ARCHIVE"

class ArchiveReason(str, enum.Enum):
    AUTO_CLEANUP = "auto_cleanup"
    MANUAL_ARCHIVE = "manual_archive"
    RETENTION_POLICY = "retention_policy"
    SYSTEM_CLEANUP = "system_cleanup"


# VERITABANI MODELLERININ TANIMI
# ==============================================================

# Base class for all models
Base = declarative_base()

# Base Model
class BaseModel(Base):
    """
    Base model with UUID primary key and common fields
    Tüm modeller için UUID tabanlı ortak alanlar ve metodlar
    """
    __abstract__ = True
    __allow_unmapped__ = True  # Allow legacy annotations
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def to_dict(self) -> dict:
        """Model'i dictionary'ye çevir"""
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            if isinstance(value, datetime):
                value = value.isoformat()
            elif isinstance(value, enum.Enum):
                value = value.value
            elif hasattr(value, 'to_dict'):  # Nested object support
                value = value.to_dict()
            result[column.name] = value
        return result
    
    def __repr__(self) -> str:
        """Model string representation"""
        return f"<{self.__class__.__name__}(id={self.id})>"
    
# Workflows Table
class Workflow(BaseModel):
    """
    Workflow modeli - İş akışlarını temsil eder
    """
    __tablename__ = 'workflows'

    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    status = Column(Enum(WorkflowStatus), default=WorkflowStatus.DRAFT, nullable=False)
    priority = Column(Integer, default=0, nullable=False)

    # Relationships
    nodes: List["Node"] = relationship("Node", back_populates="workflow", cascade="all, delete-orphan")
    edges: List["Edge"] = relationship("Edge", back_populates="workflow", cascade="all, delete-orphan")
    executions: List["Execution"] = relationship("Execution", back_populates="workflow", cascade="all, delete-orphan")
    triggers: List["Trigger"] = relationship("Trigger", back_populates="workflow", cascade="all, delete-orphan")

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
    language = Column(Enum(ScriptType), nullable=False)
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
    priority = Column(Integer, default=0, nullable=False)
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
]