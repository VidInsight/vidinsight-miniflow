#!/usr/bin/env python3
"""
Mock Execution Engine

Bu engine gerçek task execution'ı simüle eder:
- Predefined results döner
- Processing time simüle eder
- Parameter replacement yapar
- Farklı node type'ları destekler
"""

import time
import json
import random
from typing import Dict, Any, Optional
from datetime import datetime


class MockExecutionEngine:
    """
    Mock execution engine - gerçek task execution'ı simüle eder
    
    Bu engine test amaçlı olarak:
    - Farklı node type'ları için predefined results döner
    - Gerçekçi processing time simüle eder
    - Parameter replacement ve context handling yapar
    - Success/failure scenarios destekler
    """
    
    def __init__(self, failure_rate: float = 0.0):
        """
        Args:
            failure_rate: 0.0-1.0 arası, task failure simülasyon oranı
        """
        self.failure_rate = failure_rate
        self.execution_count = 0
        self.predefined_results = self._initialize_predefined_results()
    
    def _initialize_predefined_results(self) -> Dict[str, Dict[str, Any]]:
        """Predefined results for different node types"""
        return {
            "extract": {
                "output": {
                    "data": [
                        {"id": 1, "name": "John Doe", "email": "john@example.com", "age": 30},
                        {"id": 2, "name": "Jane Smith", "email": "jane@example.com", "age": 25},
                        {"id": 3, "name": "Bob Johnson", "email": "bob@example.com", "age": 35}
                    ],
                    "metadata": {
                        "source": "test_database",
                        "extracted_at": datetime.now().isoformat(),
                        "record_count": 3,
                        "query_time_ms": 45
                    }
                },
                "metrics": {
                    "execution_time_ms": 1200,
                    "memory_usage_mb": 15.2,
                    "cpu_usage_percent": 12.5
                }
            },
            
            "transform": {
                "result": {
                    "processed_data": [
                        {"id": 1, "name": "JOHN DOE", "email": "john@example.com", "age": 30, "age_group": "adult"},
                        {"id": 2, "name": "JANE SMITH", "email": "jane@example.com", "age": 25, "age_group": "adult"},
                        {"id": 3, "name": "BOB JOHNSON", "email": "bob@example.com", "age": 35, "age_group": "adult"}
                    ],
                    "transformations_applied": [
                        "name_uppercase",
                        "age_group_classification",
                        "email_validation"
                    ],
                    "processed_at": datetime.now().isoformat()
                },
                "statistics": {
                    "input_records": 3,
                    "output_records": 3,
                    "transformation_success_rate": 100.0,
                    "data_quality_score": 95.5
                },
                "metrics": {
                    "execution_time_ms": 800,
                    "memory_usage_mb": 22.1,
                    "cpu_usage_percent": 18.3
                }
            },
            
            "load": {
                "confirmation": {
                    "status": "success",
                    "loaded_records": 3,
                    "destination": "analytics_db",
                    "table": "processed_users",
                    "loaded_at": datetime.now().isoformat(),
                    "transaction_id": "txn_" + str(random.randint(100000, 999999))
                },
                "performance": {
                    "insert_time_ms": 350,
                    "index_update_time_ms": 120,
                    "total_time_ms": 470
                },
                "metrics": {
                    "execution_time_ms": 600,
                    "memory_usage_mb": 8.7,
                    "cpu_usage_percent": 5.2
                }
            },
            
            # Generic task type for other scenarios
            "task": {
                "output": {
                    "status": "completed",
                    "result": "Task executed successfully",
                    "timestamp": datetime.now().isoformat(),
                    "task_id": "task_" + str(random.randint(1000, 9999))
                },
                "metrics": {
                    "execution_time_ms": 500,
                    "memory_usage_mb": 10.0,
                    "cpu_usage_percent": 8.0
                }
            }
        }
    
    def execute_task(self, task_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ana task execution fonksiyonu
        
        Args:
            task_payload: Task bilgileri (node_id, script, params, etc.)
            
        Returns:
            Execution result dict
        """
        self.execution_count += 1
        
        try:
            # Task bilgilerini çıkar
            node_id = task_payload.get('node_id', 'unknown')
            node_type = task_payload.get('type', 'task')
            script = task_payload.get('script', 'unknown.py')
            params = task_payload.get('params', {})
            
            print(f"🔧 Mock Engine: Executing task {node_id} (type: {node_type})")
            
            # Processing time simüle et
            processing_time = self._simulate_processing_time(node_type)
            time.sleep(processing_time)
            
            # Failure simülasyonu
            if self._should_simulate_failure():
                return self._create_failure_result(node_id, "Simulated task failure")
            
            # Success result oluştur
            result = self._create_success_result(node_id, node_type, script, params)
            
            print(f"✅ Mock Engine: Task {node_id} completed successfully")
            return result
            
        except Exception as e:
            print(f"❌ Mock Engine: Task execution error: {e}")
            return self._create_failure_result(
                task_payload.get('node_id', 'unknown'), 
                f"Execution error: {str(e)}"
            )
    
    def _simulate_processing_time(self, node_type: str) -> float:
        """Node type'a göre gerçekçi processing time simüle et"""
        base_times = {
            "extract": 1.0,    # Extract işlemleri daha uzun
            "transform": 0.8,  # Transform orta süre
            "load": 0.6,       # Load daha hızlı
            "task": 0.5        # Generic task
        }
        
        base_time = base_times.get(node_type, 0.5)
        # %20 varyasyon ekle
        variation = random.uniform(0.8, 1.2)
        return base_time * variation
    
    def _should_simulate_failure(self) -> bool:
        """Failure rate'e göre failure simüle edip etmeyeceğini belirle"""
        return random.random() < self.failure_rate
    
    def _create_success_result(self, node_id: str, node_type: str, script: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Success result oluştur"""
        
        # Node type'a göre predefined result al
        predefined = self.predefined_results.get(node_type, self.predefined_results["task"])
        
        # Result'ı customize et
        result_data = self._customize_result_for_node(predefined, node_id, params)
        
        return {
            "status": "success",
            "node_id": node_id,
            "execution_id": params.get("execution_id", "unknown"),
            "result": result_data,
            "metadata": {
                "script": script,
                "node_type": node_type,
                "execution_count": self.execution_count,
                "simulated": True,
                "completed_at": datetime.now().isoformat()
            }
        }
    
    def _create_failure_result(self, node_id: str, error_message: str) -> Dict[str, Any]:
        """Failure result oluştur"""
        return {
            "status": "failed",
            "node_id": node_id,
            "error": error_message,
            "metadata": {
                "execution_count": self.execution_count,
                "simulated": True,
                "failed_at": datetime.now().isoformat()
            }
        }
    
    def _customize_result_for_node(self, predefined: Dict[str, Any], node_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Node'a özel result customization"""
        
        # Deep copy predefined result
        import copy
        result = copy.deepcopy(predefined)
        
        # Node ID'yi result'a ekle
        if "metadata" in result:
            result["metadata"]["node_id"] = node_id
        
        # Parameters'dan gelen input data'yı işle
        if "input_data" in params:
            # Bu gerçek bir sistemde previous task'ın output'u olurdu
            # Test için simüle ediyoruz
            if "processed_data" in result.get("result", {}):
                # Transform node için input data'yı reference et
                result["result"]["input_reference"] = "Processed from previous task"
        
        # Timestamp'leri güncelle
        current_time = datetime.now().isoformat()
        self._update_timestamps_recursive(result, current_time)
        
        return result
    
    def _update_timestamps_recursive(self, obj: Any, timestamp: str):
        """Recursive olarak timestamp'leri güncelle"""
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key.endswith("_at") or key == "timestamp":
                    obj[key] = timestamp
                else:
                    self._update_timestamps_recursive(value, timestamp)
        elif isinstance(obj, list):
            for item in obj:
                self._update_timestamps_recursive(item, timestamp)
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """Execution istatistiklerini döner"""
        return {
            "total_executions": self.execution_count,
            "failure_rate": self.failure_rate,
            "supported_node_types": list(self.predefined_results.keys())
        }
    
    def reset_stats(self):
        """İstatistikleri sıfırla"""
        self.execution_count = 0 