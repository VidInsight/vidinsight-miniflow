from sqlalchemy import Column, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base


class Node(Base):
    __tablename__ = 'nodes'

    id = Column(String, primary_key=True)
    workflow_id = Column(String, ForeignKey('workflows.id', ondelete='CASCADE'), nullable=False)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)
    script = Column(Text)
    params = Column(Text)  # JSON string

    # Relationships
    workflow = relationship("Workflow", back_populates="nodes")
    edges_from = relationship("Edge", foreign_keys="Edge.from_node_id", back_populates="from_node")
    edges_to = relationship("Edge", foreign_keys="Edge.to_node_id", back_populates="to_node")
    execution_inputs = relationship("ExecutionInput", back_populates="node", cascade="all, delete-orphan")
    execution_outputs = relationship("ExecutionOutput", back_populates="node", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Node(id='{self.id}', name='{self.name}', type='{self.type}')>"

    def to_dict(self):
        return {
            'id': self.id,
            'workflow_id': self.workflow_id,
            'name': self.name,
            'type': self.type,
            'script': self.script,
            'params': self.params
        }

