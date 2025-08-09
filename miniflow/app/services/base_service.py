"""
Base Service  - Bu modül tüm servislerde kullanılacak ortak değişken ve metodları içerir.
"""

from typing import Any, Dict, Optional
from miniflow.main import MiniflowCore

class BaseService:
    def __init__(self, core: MiniflowCore):
        """
        BaseService sınıfının yapıcı metodu.
        """

        self.core = core
        self.orchestrator = core.orchestration