from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base


class ExecutionInput(Base):
    __tablename__ = 'execution_inputs'

    id = Column(String, primary_key=True)
    execution_id = Column(String, ForeignKey('executions.id', ondelete='CASCADE'), nullable=False)
    node_id = Column(String, ForeignKey('nodes.id', ondelete='CASCADE'), nullable=False)
    status = Column(String, default='pending')
    priority = Column(Integer, default=0)
    dependency_count = Column(Integer)

    # Relationships
    execution = relationship("Execution", back_populates="execution_inputs")
    node = relationship("Node", back_populates="execution_inputs")

    def __repr__(self):
        return f"<ExecutionInput(id='{self.id}', status='{self.status}', priority={self.priority})>"

    def to_dict(self):
        return {
            'id': self.id,
            'execution_id': self.execution_id,
            'node_id': self.node_id,
            'status': self.status,
            'priority': self.priority,
            'dependency_count': self.dependency_count
        } 