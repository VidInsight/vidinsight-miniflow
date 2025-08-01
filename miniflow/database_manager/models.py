import uuid
import enum
from typing import Optional, List
from datetime import datetime, timezone
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, JSON, Float, Boolean, Enum, UniqueConstraint


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


class ScriptType(str, enum.Enum):
    PYTHON = "python"


class ScriptTestStatus(str, enum.Enum):
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


# ======================================================================================================= BASE MODEL  ==
Base = declarative_base()

class BaseModel(Base):
    __prefix__ = "BM"
    __abstract__ = True
    __allow_unmapped__ = True

    @classmethod
    def _generate_id(cls):
        prefix = getattr(cls, '__prefix__', 'XX')
        uuid_suffix = str(uuid.uuid4()).replace('-', '')[:10].upper()
        return f"{prefix}{uuid_suffix}"

    id = Column(String(12), primary_key=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    def __init__(self, **kwargs):
        """Initialize the model with auto-generated ID if not provided"""
        if 'id' not in kwargs or kwargs['id'] is None:
            kwargs['id'] = self._generate_id()
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(id={self.id})>"

    def to_dict(self) -> dict:
        result = {}

        for column in self.__table__.columns:
            value = getattr(self, column.name)

            if isinstance(value, datetime):
                value = value.isoformat()
            elif isinstance(value, enum.Enum):
                value = value.value
            elif hasattr(value, 'to_dict'):
                value = value.to_dict()

            result[column.name] = value

        return result


# =================================================================================================== WORKFLOW MODEL  ==
class Workflow(BaseModel):
    __prefix__ = "WF"
    __tablename__ = 'workflows'

    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    status = Column(Enum(WorkflowStatus), default=WorkflowStatus.DRAFT, nullable=False)
    priority = Column(Integer, default=0, nullable=False)

    nodes: List["Node"] = relationship("Node", back_populates="workflow", cascade="all, delete-orphan")
    edges: List["Edge"] = relationship("Edge", back_populates="workflow", cascade="all, delete-orphan")
    executions: List["Execution"] = relationship("Execution", back_populates="workflow", cascade="all, delete-orphan")


# ======================================================================================================= NODE MODEL  ==
class Node(BaseModel):
    __prefix__ = "ND"
    __tablename__ = 'nodes'
    __table_args__ = (UniqueConstraint('workflow_id', 'name', name='uq_node_workflow_name'),)

    workflow_id = Column(String(12), ForeignKey('workflows.id', ondelete='CASCADE'), nullable=False)
    script_id = Column(String(12), ForeignKey('scripts.id', ondelete='SET NULL'), nullable=True)
    name = Column(String(100), nullable=False)
    params = Column(JSON, nullable=True, default=dict)
    max_retries = Column(Integer, default=3, nullable=False)
    timeout_seconds = Column(Integer, default=300, nullable=False)

    workflow: "Workflow" = relationship("Workflow", back_populates="nodes")
    script: Optional["Script"] = relationship("Script", back_populates="nodes")
    edges_from: List["Edge"] = relationship("Edge", foreign_keys="[Edge.from_node_id]", back_populates="from_node", cascade="all, delete-orphan")
    edges_to: List["Edge"] = relationship("Edge", foreign_keys="[Edge.to_node_id]", back_populates="to_node", cascade="all, delete-orphan")
    execution_inputs: List["ExecutionInput"] = relationship("ExecutionInput", back_populates="node")
    execution_outputs: List["ExecutionOutput"] = relationship("ExecutionOutput", back_populates="node")


# ======================================================================================================= EDGE MODEL  ==
class Edge(BaseModel):
    __prefix__ = "ED"
    __tablename__ = 'edges'
    __table_args__ = (UniqueConstraint('workflow_id', 'from_node_id', 'to_node_id', 'condition_type', name='uq_edge_workflow_nodes_condition'),)

    workflow_id = Column(String(12), ForeignKey('workflows.id', ondelete='CASCADE'), nullable=False)
    from_node_id = Column(String(12), ForeignKey('nodes.id', ondelete='CASCADE'), nullable=False)
    to_node_id = Column(String(12), ForeignKey('nodes.id', ondelete='CASCADE'), nullable=False)
    condition_type = Column(Enum(ConditionType), default=ConditionType.SUCCESS, nullable=False)

    workflow: "Workflow" = relationship("Workflow", back_populates="edges")
    from_node: "Node" = relationship("Node", foreign_keys=[from_node_id], back_populates="edges_from")
    to_node: "Node" = relationship("Node", foreign_keys=[to_node_id], back_populates="edges_to")


# ===================================================================================================== SCRIPT MODEL  ==
class Script(BaseModel):
    __prefix__ = "SC"
    __tablename__ = 'scripts'

    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    language = Column(Enum(ScriptType), nullable=False, default=ScriptType.PYTHON)
    script_path = Column(Text, nullable=False)
    input_params = Column(JSON, default=dict, nullable=False)
    output_params = Column(JSON, default=dict, nullable=False)
    test_status = Column(Enum(ScriptTestStatus), default=ScriptTestStatus.UNTESTED, nullable=False)

    nodes: List["Node"] = relationship("Node", back_populates="script")


# ================================================================================================== EXECUTION MODEL  ==
class Execution(BaseModel):
    __prefix__ = "EX"
    __tablename__ = 'executions'

    workflow_id = Column(String(12), ForeignKey('workflows.id', ondelete='CASCADE'), nullable=False)
    status = Column(Enum(ExecutionStatus), default=ExecutionStatus.PENDING, nullable=False)
    pending_nodes = Column(Integer, default=0, nullable=False)
    executed_nodes = Column(Integer, default=0, nullable=False)
    results = Column(JSON, default=dict, nullable=False)
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    ended_at = Column(DateTime, nullable=True)

    workflow: "Workflow" = relationship("Workflow", back_populates="executions")
    execution_inputs: List["ExecutionInput"] = relationship("ExecutionInput", back_populates="execution", cascade="all, delete-orphan")
    execution_outputs: List["ExecutionOutput"] = relationship("ExecutionOutput", back_populates="execution", cascade="all, delete-orphan")


# ============================================================================================= EXECUTION INPUT MODEL ==
class ExecutionInput(BaseModel):
    __prefix__ = "EI"
    __tablename__ = 'execution_inputs'
    __table_args__ = (UniqueConstraint('execution_id', 'node_id', name='uq_execution_input_execution_node'),)
    
    execution_id = Column(String(12), ForeignKey('executions.id', ondelete='CASCADE'), nullable=False)
    node_id = Column(String(12), ForeignKey('nodes.id', ondelete='CASCADE'), nullable=False)
    priority = Column(Integer, default=0, nullable=False)
    dependency_count = Column(Integer, default=0, nullable=False)
    wait_factor = Column(Integer, default=0, nullable=False)

    execution: "Execution" = relationship("Execution", back_populates="execution_inputs")
    node: "Node" = relationship("Node", back_populates="execution_inputs")


# ============================================================================================ EXECUTION OUTPUT MODEL ==
class ExecutionOutput(BaseModel):
    __prefix__ = "EO"
    __tablename__ = 'execution_outputs'
    __table_args__ = (UniqueConstraint('execution_id', 'node_id', name='uq_execution_output_execution_node'),)
    
    execution_id = Column(String(12), ForeignKey('executions.id', ondelete='CASCADE'), nullable=False)
    node_id = Column(String(12), ForeignKey('nodes.id', ondelete='CASCADE'), nullable=False)
    status = Column(Enum(ExecutionOutputStatus), nullable=False)
    result_data = Column(JSON, nullable=True)
    started_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)

    execution: "Execution" = relationship("Execution", back_populates="execution_outputs")
    node: "Node" = relationship("Node", back_populates="execution_outputs")


# ========================================================================================== ARCHIVED EXECUTION MODEL ==
class ArchivedExecution(BaseModel):
    __prefix__ = "AE"
    __tablename__ = 'archived_executions'

    original_execution_id = Column(String(12), unique=True, nullable=False)
    workflow_id = Column(String(12), ForeignKey('workflows.id'), nullable=False)
    status = Column(Enum(ExecutionStatus), nullable=False)
    success = Column(Boolean, default=False, nullable=False)
    results = Column(JSON, default=dict, nullable=False)
    started_at = Column(DateTime, nullable=False)
    ended_at = Column(DateTime, nullable=True)
    archived_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    archive_reason = Column(Enum(ArchiveReason), default=ArchiveReason.AUTO_CLEANUP, nullable=False)

    workflow: "Workflow" = relationship("Workflow")


# =================================================================================================== AUDIT LOG MODEL ==
class AuditLog(BaseModel):
    __prefix__ = "AL"
    __tablename__ = 'audit_logs'
    
    table_name = Column(String(100), nullable=False)
    record_id = Column(String(12), nullable=False)
    action = Column(Enum(AuditAction), nullable=False)
    old_values = Column(JSON, nullable=True)
    new_values = Column(JSON, nullable=True)