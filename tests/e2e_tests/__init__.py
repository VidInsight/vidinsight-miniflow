"""
END-TO-END TESTS MODULE
======================

Bu modül Miniflow sisteminin end-to-end testlerini içerir.
Tam sistem akışını ve kullanıcı senaryolarını test eder.

TEST CATEGORIES:
===============
• Complete workflow lifecycle tests
• User scenario tests
• Performance tests
• Stress tests
• System health tests

TEST STRUCTURE:
==============
e2e_tests/
├── __init__.py
├── test_workflow_lifecycle.py  # Complete workflow tests
├── test_user_scenarios.py      # User workflow scenarios
├── test_performance.py         # Performance benchmarks
├── test_stress.py             # Stress and load tests
└── test_system_health.py      # System health monitoring

USAGE:
======
pytest tests/e2e_tests/ -v --tb=short
pytest tests/e2e_tests/test_workflow_lifecycle.py -v
"""

# E2E test markers
import pytest

@pytest.mark.e2e
class TestE2EMarkers:
    """End-to-end test marker definitions"""
    pass
