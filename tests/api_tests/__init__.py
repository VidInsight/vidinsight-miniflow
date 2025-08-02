"""
API TESTS MODULE
===============

Bu modül Miniflow API endpoint'lerinin testlerini içerir.
FastAPI uygulamasının REST API fonksiyonalitesini test eder.

TEST CATEGORIES:
===============
• Workflow API tests
• Script API tests  
• Execution API tests
• Health check tests
• Error handling tests

TEST STRUCTURE:
==============
api_tests/
├── __init__.py
├── test_workflow_api.py      # Workflow CRUD operations
├── test_script_api.py        # Script CRUD operations
├── test_execution_api.py     # Execution management
├── test_health_api.py        # Health check endpoints
└── test_error_handling.py    # Error response tests

USAGE:
======
pytest tests/api_tests/ -v --tb=short
pytest tests/api_tests/test_workflow_api.py -v
"""

# API test markers
import pytest

@pytest.mark.api
class TestAPIMarkers:
    """API test marker definitions"""
    pass
