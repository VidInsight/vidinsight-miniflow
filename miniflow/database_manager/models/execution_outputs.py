from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base


class ExecutionOutput(Base):
    __tablename__ = 'execution_outputs'

    id = Column(String, primary_key=True)
    execution_id = Column(String, ForeignKey('executions.id', ondelete='CASCADE'), nullable=False)
    node_id = Column(String, ForeignKey('nodes.id', ondelete='CASCADE'), nullable=False)
    status = Column(String, nullable=False)
    result_data = Column(Text)  # JSON string
    error_message = Column(Text)
    started_at = Column(DateTime)
    ended_at = Column(DateTime)

    # Relationships
    execution = relationship("Execution", back_populates="execution_outputs")
    node = relationship("Node", back_populates="execution_outputs")

    def __repr__(self):
        return f"<ExecutionOutput(id='{self.id}', status='{self.status}', node_id='{self.node_id}')>"

    def to_dict(self):
        return {
            'id': self.id,
            'execution_id': self.execution_id,
            'node_id': self.node_id,
            'status': self.status,
            'result_data': self.result_data,
            'error_message': self.error_message,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'ended_at': self.ended_at.isoformat() if self.ended_at else None
        } 