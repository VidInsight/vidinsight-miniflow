from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base


class Edge(Base):
    __tablename__ = 'edges'

    id = Column(String, primary_key=True)
    workflow_id = Column(String, ForeignKey('workflows.id', ondelete='CASCADE'), nullable=False)
    from_node_id = Column(String, ForeignKey('nodes.id', ondelete='CASCADE'), nullable=False)
    to_node_id = Column(String, ForeignKey('nodes.id', ondelete='CASCADE'), nullable=False)
    condition_type = Column(String, default='success')

    # Relationships
    workflow = relationship("Workflow", back_populates="edges")
    from_node = relationship("Node", foreign_keys=[from_node_id], back_populates="edges_from")
    to_node = relationship("Node", foreign_keys=[to_node_id], back_populates="edges_to")

    def __repr__(self):
        return f"<Edge(id='{self.id}', from='{self.from_node_id}', to='{self.to_node_id}')>"

    def to_dict(self):
        return {
            'id': self.id,
            'workflow_id': self.workflow_id,
            'from_node_id': self.from_node_id,
            'to_node_id': self.to_node_id,
            'condition_type': self.condition_type
        }

