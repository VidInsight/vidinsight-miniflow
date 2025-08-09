"""
Web API modülü

Bu modül web uygulaması için gerekli tüm API endpoint'lerini içerir:
- workflows: Workflow yönetimi
- nodes: Node yönetimi
- edges: Edge yönetimi
- environment_variables: Environment variable yönetimi
- scripts: Script yönetimi
- executions: Execution yönetimi
"""

from .bff_router import router

__all__ = ["router"]
