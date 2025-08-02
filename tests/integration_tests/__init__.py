"""
INTEGRATION TESTS MODULE
======================

Bu modül Miniflow bileşenleri arası entegrasyon testlerini içerir.
Bileşenlerin birlikte çalışmasını test eder.

TEST CATEGORIES:
===============
• Core integration tests
• Database integration tests
• Engine integration tests
• Scheduler integration tests
• End-to-end workflow tests

TEST STRUCTURE:
==============
integration_tests/
├── __init__.py
├── test_orchestration.py      # Core orchestration tests
├── test_database_integration.py # Database workflow tests
├── test_engine_integration.py   # Execution engine tests
├── test_scheduler_integration.py # Scheduler workflow tests
└── test_workflow_integration.py # Complete workflow tests

USAGE:
======
pytest tests/integration_tests/ -v --tb=short
pytest tests/integration_tests/test_orchestration.py -v
"""

# Integration test markers
import pytest

@pytest.mark.integration
class TestIntegrationMarkers:
    """Integration test marker definitions"""
    pass
