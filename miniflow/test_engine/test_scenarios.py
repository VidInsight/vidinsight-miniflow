#!/usr/bin/env python3
"""
Test Scenarios and Workflow Definitions

Bu modül test amaçlı workflow'lar ve scenarios içerir:
- Test workflow JSON definitions
- Predefined results mapping
- Test data generators
- Scenario configurations
"""

import json
from typing import Dict, Any, List


def create_test_workflow() -> Dict[str, Any]:
    """
    Comprehensive test workflow oluştur
    
    Bu workflow complete data pipeline'ı simüle eder:
    - Extract: Veri çekme
    - Transform: Veri işleme  
    - Load: Veri yükleme
    
    Returns:
        Test workflow JSON
    """
    return {
        "name": "Test Data Pipeline",
        "description": "Complete test workflow for end-to-end validation - Extract, Transform, Load pipeline",
        "version": "1.0",
        "triggers": [],  # Manual trigger only
        "steps": [
            {
                "type": "extract",
                "name": "data_extractor",
                "script": "extract_data.py",
                "parameters": {
                    "source": "test_database",
                    "query": "SELECT * FROM users WHERE active = 1",
                    "connection_timeout": 30,
                    "batch_size": 1000
                }
            },
            {
                "type": "transform", 
                "name": "data_transformer",
                "script": "transform_data.py",
                "parameters": {
                    "input_data": "{{ data_extractor.output }}",
                    "operation": "clean_and_normalize",
                    "validation_rules": {
                        "email_format": True,
                        "age_range": [18, 100],
                        "required_fields": ["name", "email"]
                    },
                    "transformations": [
                        "uppercase_names",
                        "validate_emails", 
                        "categorize_age_groups"
                    ]
                }
            },
            {
                "type": "load",
                "name": "data_loader", 
                "script": "load_data.py",
                "parameters": {
                    "processed_data": "{{ data_transformer.result }}",
                    "destination": "analytics_db",
                    "table": "processed_users",
                    "mode": "insert",
                    "batch_size": 500,
                    "create_backup": True
                }
            }
        ],
        "connections": [
            {"from": "data_extractor", "to": "data_transformer"},
            {"from": "data_transformer", "to": "data_loader"}
        ]
    }


def create_simple_test_workflow() -> Dict[str, Any]:
    """
    Basit test workflow oluştur (hızlı testler için)
    
    Returns:
        Simple test workflow JSON
    """
    return {
        "name": "Simple Test Workflow",
        "description": "Simple 2-step workflow for quick testing",
        "version": "1.0", 
        "triggers": [],
        "steps": [
            {
                "type": "task",
                "name": "step1",
                "script": "process_step1.py",
                "parameters": {
                    "input": "test_data",
                    "mode": "process"
                }
            },
            {
                "type": "task",
                "name": "step2", 
                "script": "process_step2.py",
                "parameters": {
                    "input_data": "{{ step1.output }}",
                    "final_step": True
                }
            }
        ],
        "connections": [
            {"from": "step1", "to": "step2"}
        ]
    }


def create_complex_test_workflow() -> Dict[str, Any]:
    """
    Karmaşık test workflow oluştur (advanced testing için)
    
    Returns:
        Complex test workflow JSON
    """
    return {
        "name": "Complex Multi-Branch Workflow",
        "description": "Complex workflow with parallel branches and multiple dependencies",
        "version": "1.0",
        "triggers": [],
        "steps": [
            {
                "type": "extract",
                "name": "source_a",
                "script": "extract_source_a.py", 
                "parameters": {
                    "source": "database_a",
                    "query": "SELECT * FROM table_a"
                }
            },
            {
                "type": "extract", 
                "name": "source_b",
                "script": "extract_source_b.py",
                "parameters": {
                    "source": "database_b", 
                    "query": "SELECT * FROM table_b"
                }
            },
            {
                "type": "transform",
                "name": "process_a",
                "script": "process_a.py",
                "parameters": {
                    "input_data": "{{ source_a.output }}",
                    "operation": "clean_data_a"
                }
            },
            {
                "type": "transform",
                "name": "process_b", 
                "script": "process_b.py",
                "parameters": {
                    "input_data": "{{ source_b.output }}",
                    "operation": "clean_data_b"
                }
            },
            {
                "type": "transform",
                "name": "merge_data",
                "script": "merge_data.py",
                "parameters": {
                    "data_a": "{{ process_a.result }}",
                    "data_b": "{{ process_b.result }}",
                    "merge_key": "id"
                }
            },
            {
                "type": "load",
                "name": "final_load",
                "script": "load_final.py", 
                "parameters": {
                    "merged_data": "{{ merge_data.result }}",
                    "destination": "final_db"
                }
            }
        ],
        "connections": [
            {"from": "source_a", "to": "process_a"},
            {"from": "source_b", "to": "process_b"},
            {"from": "process_a", "to": "merge_data"},
            {"from": "process_b", "to": "merge_data"},
            {"from": "merge_data", "to": "final_load"}
        ]
    }


def get_predefined_results() -> Dict[str, Dict[str, Any]]:
    """
    Test scenarios için predefined results
    
    Returns:
        Node type'a göre predefined results mapping
    """
    return {
        "extract": {
            "output": {
                "data": [
                    {"id": 1, "name": "John Doe", "email": "john@example.com", "age": 30, "active": 1},
                    {"id": 2, "name": "Jane Smith", "email": "jane@example.com", "age": 25, "active": 1},
                    {"id": 3, "name": "Bob Johnson", "email": "bob@example.com", "age": 35, "active": 1},
                    {"id": 4, "name": "Alice Brown", "email": "alice@example.com", "age": 28, "active": 1},
                    {"id": 5, "name": "Charlie Wilson", "email": "charlie@example.com", "age": 42, "active": 1}
                ],
                "metadata": {
                    "source": "test_database",
                    "table": "users",
                    "extracted_at": "2024-01-15T10:30:00Z",
                    "record_count": 5,
                    "query_time_ms": 125,
                    "connection_pool": "pool_1"
                }
            },
            "metrics": {
                "execution_time_ms": 1500,
                "memory_usage_mb": 18.5,
                "cpu_usage_percent": 15.2,
                "network_io_kb": 245
            }
        },
        
        "transform": {
            "result": {
                "processed_data": [
                    {"id": 1, "name": "JOHN DOE", "email": "john@example.com", "age": 30, "age_group": "adult", "email_valid": True},
                    {"id": 2, "name": "JANE SMITH", "email": "jane@example.com", "age": 25, "age_group": "adult", "email_valid": True},
                    {"id": 3, "name": "BOB JOHNSON", "email": "bob@example.com", "age": 35, "age_group": "adult", "email_valid": True},
                    {"id": 4, "name": "ALICE BROWN", "email": "alice@example.com", "age": 28, "age_group": "adult", "email_valid": True},
                    {"id": 5, "name": "CHARLIE WILSON", "email": "charlie@example.com", "age": 42, "age_group": "adult", "email_valid": True}
                ],
                "transformations_applied": [
                    "uppercase_names",
                    "validate_emails",
                    "categorize_age_groups"
                ],
                "validation_results": {
                    "total_records": 5,
                    "valid_records": 5,
                    "invalid_records": 0,
                    "validation_errors": []
                },
                "processed_at": "2024-01-15T10:31:30Z"
            },
            "statistics": {
                "input_records": 5,
                "output_records": 5,
                "transformation_success_rate": 100.0,
                "data_quality_score": 98.5,
                "processing_speed_records_per_sec": 125.5
            },
            "metrics": {
                "execution_time_ms": 950,
                "memory_usage_mb": 25.8,
                "cpu_usage_percent": 22.1
            }
        },
        
        "load": {
            "confirmation": {
                "status": "success",
                "loaded_records": 5,
                "destination": "analytics_db",
                "table": "processed_users",
                "loaded_at": "2024-01-15T10:32:15Z",
                "transaction_id": "txn_789456123",
                "backup_created": True,
                "backup_location": "/backups/processed_users_20240115_103215.sql"
            },
            "performance": {
                "insert_time_ms": 420,
                "index_update_time_ms": 180,
                "backup_time_ms": 250,
                "total_time_ms": 850
            },
            "validation": {
                "records_inserted": 5,
                "records_verified": 5,
                "integrity_check": "passed",
                "constraint_violations": 0
            },
            "metrics": {
                "execution_time_ms": 850,
                "memory_usage_mb": 12.3,
                "cpu_usage_percent": 8.7,
                "disk_io_mb": 2.1
            }
        },
        
        "task": {
            "output": {
                "status": "completed",
                "result": "Generic task executed successfully",
                "timestamp": "2024-01-15T10:30:00Z",
                "task_id": "task_generic_001"
            },
            "metrics": {
                "execution_time_ms": 500,
                "memory_usage_mb": 10.0,
                "cpu_usage_percent": 8.0
            }
        }
    }


def create_test_scenario_config() -> Dict[str, Any]:
    """
    Test scenario configuration
    
    Returns:
        Test configuration dict
    """
    return {
        "test_settings": {
            "execution_delay_ms": 1000,  # Simulated processing time
            "failure_rate": 0.0,         # 0% failure rate for successful tests
            "queue_monitoring_interval": 2.0,
            "max_test_duration_seconds": 60
        },
        
        "database_validation": {
            "check_tables": [
                "workflows",
                "nodes", 
                "edges",
                "executions",
                "execution_queue",
                "execution_results"
            ],
            "expected_counts": {
                "workflows": 1,
                "nodes": 3,
                "edges": 2,
                "executions": 1,
                "execution_queue": 3,
                "execution_results": 3  # After completion
            }
        },
        
        "workflow_validation": {
            "parameter_mapping_check": True,
            "dependency_resolution_check": True,
            "data_flow_validation": True,
            "result_consistency_check": True
        },
        
        "performance_thresholds": {
            "max_workflow_load_time_ms": 5000,
            "max_trigger_time_ms": 3000,
            "max_task_execution_time_ms": 10000,
            "max_total_workflow_time_ms": 30000
        }
    }


def save_test_workflow_to_file(workflow: Dict[str, Any], filename: str) -> str:
    """
    Test workflow'u dosyaya kaydet
    
    Args:
        workflow: Workflow JSON
        filename: Dosya adı
        
    Returns:
        Dosya yolu
    """
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(workflow, f, indent=2, ensure_ascii=False)
        
        print(f"📁 Test workflow saved to: {filename}")
        return filename
        
    except Exception as e:
        print(f"❌ Error saving test workflow: {e}")
        raise


def get_test_workflows() -> Dict[str, Dict[str, Any]]:
    """
    Tüm test workflow'larını döner
    
    Returns:
        Test workflow'lar dict
    """
    return {
        "simple": create_simple_test_workflow(),
        "standard": create_test_workflow(),
        "complex": create_complex_test_workflow()
    } 