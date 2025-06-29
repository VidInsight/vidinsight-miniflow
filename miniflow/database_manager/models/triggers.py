from sqlalchemy import Column, String, Text, Integer, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base


class Trigger(Base):
    __tablename__ = 'triggers'

    id = Column(String, primary_key=True)
    workflow_id = Column(String, ForeignKey('workflows.id', ondelete='CASCADE'), nullable=False)
    trigger_type = Column(String, nullable=False)
    config = Column(Text, default='{}')  # JSON string
    is_active = Column(Integer, default=1)

    # Relationships
    workflow = relationship("Workflow", back_populates="triggers")

    def __repr__(self):
        return f"<Trigger(id='{self.id}', type='{self.trigger_type}', active={bool(self.is_active)})>"

    def to_dict(self):
        return {
            'id': self.id,
            'workflow_id': self.workflow_id,
            'trigger_type': self.trigger_type,
            'config': self.config,
            'is_active': bool(self.is_active)
        } 