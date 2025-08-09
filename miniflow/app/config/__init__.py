"""
Configuration Module

Application configuration settings and middleware setup
"""

from .settings import Settings

try:
    from .middleware import setup_middleware
    _MIDDLEWARE_AVAILABLE = True
except ImportError:
    _MIDDLEWARE_AVAILABLE = False

try:
    from .security import *
    _SECURITY_AVAILABLE = True
except ImportError:
    _SECURITY_AVAILABLE = False

__all__ = ["Settings"]

if _MIDDLEWARE_AVAILABLE:
    __all__.append("setup_middleware")

# Security modules will be added to __all__ automatically if available
