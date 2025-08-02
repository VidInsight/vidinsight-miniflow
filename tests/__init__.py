"""
MINIFLOW TEST SUITE
==================

Bu paket Miniflow projesinin tüm testlerini içerir.
Kapsamlı test coverage sağlar.

TEST STRUCTURE:
==============
tests/
├── __init__.py                 # This file
├── conftest.py                 # Pytest configuration
├── test_data/                  # Test data and fixtures
├── unit_tests/                 # Unit tests
├── integration_tests/          # Integration tests
├── e2e_tests/                 # End-to-end tests
└── api_tests/                 # API tests

TEST COVERAGE:
==============
• Unit Tests: Individual component testing
• Integration Tests: Component interaction testing
• E2E Tests: Complete system workflow testing
• API Tests: REST API endpoint testing

RUNNING TESTS:
==============
# All tests
pytest tests/ -v

# Specific test categories
pytest tests/unit_tests/ -v
pytest tests/integration_tests/ -v
pytest tests/e2e_tests/ -v
pytest tests/api_tests/ -v

# With markers
pytest -m unit -v
pytest -m integration -v
pytest -m e2e -v
pytest -m api -v

# Performance tests
pytest -m slow -v

# Coverage report
pytest --cov=miniflow --cov-report=html
"""

# Test suite version
__version__ = "1.0.0"
__author__ = "Miniflow Development Team"
