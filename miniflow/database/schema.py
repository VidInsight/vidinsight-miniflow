# database/schema.py
from sqlalchemy import Column, String, Text, Integer, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .config import Base


class Workflow(Base):
    __tablename__ = 'workflows'

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    status = Column(String, default='active')
    version = Column(Integer, default=1)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    nodes = relationship("Node", back_populates="workflow", cascade="all, delete-orphan")
    edges = relationship("Edge", back_populates="workflow", cascade="all, delete-orphan")
    executions = relationship("Execution", back_populates="workflow", cascade="all, delete-orphan")
    triggers = relationship("Trigger", back_populates="workflow", cascade="all, delete-orphan")


class Node(Base):
    __tablename__ = 'nodes'

    id = Column(String, primary_key=True)
    workflow_id = Column(String, ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)
    script = Column(Text)
    params = Column(Text)

    workflow = relationship("Workflow", back_populates="nodes")
    from_edges = relationship("Edge", foreign_keys="[Edge.from_node_id]", back_populates="from_node")
    to_edges = relationship("Edge", foreign_keys="[Edge.to_node_id]", back_populates="to_node")


class Edge(Base):
    __tablename__ = 'edges'

    id = Column(String, primary_key=True)
    workflow_id = Column(String, ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False)
    from_node_id = Column(String, ForeignKey("nodes.id", ondelete="CASCADE"), nullable=False)
    to_node_id = Column(String, ForeignKey("nodes.id", ondelete="CASCADE"), nullable=False)
    condition_type = Column(String, default='success')

    workflow = relationship("Workflow", back_populates="edges")
    from_node = relationship("Node", foreign_keys=[from_node_id])
    to_node = relationship("Node", foreign_keys=[to_node_id])


class Execution(Base):
    __tablename__ = 'executions'

    id = Column(String, primary_key=True)
    workflow_id = Column(String, ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False)
    status = Column(String, default='pending')
    results = Column(Text, default='{}')
    started_at = Column(DateTime, default=func.now())
    ended_at = Column(DateTime, default=func.now())

    workflow = relationship("Workflow", back_populates="executions")
    tasks = relationship("ExecutionQueue", back_populates="execution", cascade="all, delete-orphan")
    records = relationship("ExecutionResult", back_populates="execution", cascade="all, delete-orphan")


class ExecutionQueue(Base):
    __tablename__ = 'execution_queue'

    id = Column(String, primary_key=True)
    execution_id = Column(String, ForeignKey("executions.id", ondelete="CASCADE"), nullable=False)
    node_id = Column(String, ForeignKey("nodes.id", ondelete="CASCADE"), nullable=False)
    status = Column(String, default='pending')
    priority = Column(Integer, default=0)
    dependency_count = Column(Integer)

    execution = relationship("Execution", back_populates="tasks")
    node = relationship("Node")


class ExecutionResult(Base):
    __tablename__ = 'execution_results'

    id = Column(String, primary_key=True)
    execution_id = Column(String, ForeignKey("executions.id", ondelete="CASCADE"), nullable=False)
    node_id = Column(String, ForeignKey("nodes.id", ondelete="CASCADE"), nullable=False)
    status = Column(String, nullable=False)
    result_data = Column(Text)
    error_message = Column(Text)
    started_at = Column(DateTime)
    ended_at = Column(DateTime)

    execution = relationship("Execution", back_populates="records")
    node = relationship("Node")


class Trigger(Base):
    __tablename__ = 'triggers'

    id = Column(String, primary_key=True)
    workflow_id = Column(String, ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False)
    trigger_type = Column(String, nullable=False)
    config = Column(Text, default='{}')
    is_active = Column(Integer, default=1)

    workflow = relationship("Workflow", back_populates="triggers")
