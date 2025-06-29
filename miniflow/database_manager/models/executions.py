from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base


class Execution(Base):
    __tablename__ = 'executions'

    id = Column(String, primary_key=True)
    workflow_id = Column(String, ForeignKey('workflows.id', ondelete='CASCADE'), nullable=False)
    status = Column(String, default='pending')
    results = Column(Text, default='{}')  # JSON string
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    workflow = relationship("Workflow", back_populates="executions")
    execution_inputs = relationship("ExecutionInput", back_populates="execution", cascade="all, delete-orphan")
    execution_outputs = relationship("ExecutionOutput", back_populates="execution", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Execution(id='{self.id}', workflow_id='{self.workflow_id}', status='{self.status}')>"

    def to_dict(self):
        return {
            'id': self.id,
            'workflow_id': self.workflow_id,
            'status': self.status,
            'results': self.results,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'ended_at': self.ended_at.isoformat() if self.ended_at else None
        }

