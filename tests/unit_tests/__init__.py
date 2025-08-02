"""
UNIT TESTS MODULE
===============

Bu modül Miniflow bileşenlerinin unit testlerini içerir.
Her modülün bağımsız olarak test edilmesini sağlar.

TEST CATEGORIES:
===============
• Database Manager tests
• Parallelism Engine tests
• Scheduler tests
• Utils tests
• Exception handling tests

TEST STRUCTURE:
==============
unit_tests/
├── __init__.py
├── test_database_manager/     # Database related tests
│   ├── test_config.py
│   ├── test_models.py
│   └── test_crud/
├── test_parallelism_engine/   # Execution engine tests
│   ├── test_manager.py
│   ├── test_process_controller.py
│   └── test_queue_controller.py
├── test_scheduler/            # Scheduler tests
│   ├── test_input_monitor.py
│   └── test_output_monitor.py
├── test_utils/               # Utility function tests
│   ├── test_miniflow_logger.py
│   └── test_utility_functions.py
└── test_exceptions.py        # Exception handling tests

USAGE:
======
pytest tests/unit_tests/ -v --tb=short
pytest tests/unit_tests/test_database_manager/ -v
"""

# Unit test configuration
# Custom markers are defined in pytest.ini
