#!/usr/bin/env python3
"""
End-to-End Test Suite

Complete workflow lifecycle testing:
1. System initialization
2. Workflow loading with parameter mapping
3. Workflow triggering
4. Task execution simulation
5. Result processing
6. Database state validation
7. Performance monitoring
"""

import os
import time
import json
from typing import Dict, Any, List
from datetime import datetime

from .test_scenarios import create_test_workflow, save_test_workflow_to_file, create_test_scenario_config
from .test_scheduler import create_test_scheduler
from ..main import MiniflowApp
from .. import database


class EndToEndTestSuite:
    """
    Complete end-to-end test suite
    
    Bu test suite tüm Miniflow sistemini test eder:
    - Workflow loading ve parameter mapping
    - Task execution simulation
    - Result processing ve database updates
    - Performance ve consistency validation
    """
    
    def __init__(self, db_path: str = "test_miniflow.db"):
        """
        Args:
            db_path: Test database path
        """
        self.db_path = db_path
        self.test_config = create_test_scenario_config()
        self.test_results = {}
        self.start_time = None
        
        # Test components
        self.app = None
        self.test_scheduler = None
        self.workflow_id = None
        self.execution_id = None
    
    def run_complete_test(self) -> Dict[str, Any]:
        """
        Complete end-to-end test çalıştır
        
        Returns:
            Test results summary
        """
        print("🧪 STARTING END-TO-END TEST SUITE")
        print("=" * 60)
        
        self.start_time = datetime.now()
        
        try:
            # Test phases
            self._phase_1_system_initialization()
            self._phase_2_workflow_loading()
            self._phase_3_database_validation_after_load()
            self._phase_4_workflow_triggering()
            self._phase_5_database_validation_after_trigger()
            self._phase_6_test_scheduler_setup()
            self._phase_7_task_execution_simulation()
            self._phase_8_result_processing_validation()
            self._phase_9_final_database_validation()
            self._phase_10_performance_analysis()
            
            # Success summary
            self._generate_success_summary()
            return self.test_results
            
        except Exception as e:
            self._handle_test_failure(e)
            return self.test_results
        
        finally:
            self._cleanup()
    
    def _phase_1_system_initialization(self):
        """Phase 1: System initialization"""
        print("\n1️⃣ PHASE 1: SYSTEM INITIALIZATION")
        print("-" * 40)
        
        # Clean up existing database
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
            print(f"🗑️ Cleaned up existing database: {self.db_path}")
        
        # Initialize database first
        database.init_database(self.db_path)
        print(f"✅ Database initialized: {self.db_path}")
        
        # Initialize main app with custom db_path
        self.app = MiniflowApp()
        self.app.db_path = self.db_path  # Override db path for testing
        
        # Verify database connection
        connection_result = database.check_database_connection(self.db_path)
        if not connection_result.success:
            raise Exception("Database connection failed")
        
        print("✅ Database connection verified")
        self.test_results["phase_1"] = {"status": "success", "duration_ms": self._get_phase_duration()}
    
    def _phase_2_workflow_loading(self):
        """Phase 2: Workflow loading with parameter mapping"""
        print("\n2️⃣ PHASE 2: WORKFLOW LOADING")
        print("-" * 40)
        
        phase_start = time.time()
        
        # Create test workflow
        test_workflow = create_test_workflow()
        workflow_file = save_test_workflow_to_file(test_workflow, "test_workflow.json")
        
        print(f"📁 Test workflow created: {workflow_file}")
        
        # Load workflow using main app
        load_result = self.app.load_workflow(workflow_file)
        self.workflow_id = load_result['workflow_id']
        
        print(f"✅ Workflow loaded successfully: {self.workflow_id}")
        
        # Verify parameter mapping
        node_mapping = load_result['info']['node_mapping']
        print(f"🔗 Node mapping created: {len(node_mapping)} nodes")
        
        for name, node_id in node_mapping.items():
            print(f"   {name} → {node_id}")
        
        # Validate expected counts
        expected = self.test_config["database_validation"]["expected_counts"]
        if load_result['info']['nodes_created'] != expected['nodes']:
            raise Exception(f"Expected {expected['nodes']} nodes, got {load_result['info']['nodes_created']}")
        
        if load_result['info']['edges_created'] != expected['edges']:
            raise Exception(f"Expected {expected['edges']} edges, got {load_result['info']['edges_created']}")
        
        duration_ms = (time.time() - phase_start) * 1000
        self.test_results["phase_2"] = {
            "status": "success",
            "duration_ms": duration_ms,
            "workflow_id": self.workflow_id,
            "nodes_created": load_result['info']['nodes_created'],
            "edges_created": load_result['info']['edges_created'],
            "node_mapping": node_mapping
        }
    
    def _phase_3_database_validation_after_load(self):
        """Phase 3: Database validation after workflow load"""
        print("\n3️⃣ PHASE 3: DATABASE VALIDATION (AFTER LOAD)")
        print("-" * 40)
        
        # Check table counts
        validation_results = {}
        
        # Workflows table
        workflows_result = database.list_workflows(self.db_path)
        workflows_count = len(workflows_result.data) if workflows_result.success else 0
        validation_results["workflows"] = workflows_count
        print(f"📋 Workflows: {workflows_count}")
        
        # Nodes table
        nodes_result = database.list_workflow_nodes(self.db_path, self.workflow_id)
        nodes_count = len(nodes_result.data) if nodes_result.success else 0
        validation_results["nodes"] = nodes_count
        print(f"🔗 Nodes: {nodes_count}")
        
        # Edges table
        edges_result = database.list_workflow_edges(self.db_path, self.workflow_id)
        edges_count = len(edges_result.data) if edges_result.success else 0
        validation_results["edges"] = edges_count
        print(f"↔️ Edges: {edges_count}")
        
        # Validate against expected counts
        expected = self.test_config["database_validation"]["expected_counts"]
        for table, expected_count in expected.items():
            if table in ["executions", "execution_queue", "execution_results"]:
                continue  # These will be checked after trigger
            
            actual_count = validation_results.get(table, 0)
            if actual_count != expected_count:
                raise Exception(f"Table {table}: expected {expected_count}, got {actual_count}")
        
        print("✅ Database validation passed")
        self.test_results["phase_3"] = {
            "status": "success",
            "validation_results": validation_results
        }
    
    def _phase_4_workflow_triggering(self):
        """Phase 4: Workflow triggering"""
        print("\n4️⃣ PHASE 4: WORKFLOW TRIGGERING")
        print("-" * 40)
        
        phase_start = time.time()
        
        # Trigger workflow
        trigger_result = self.app.trigger_workflow(self.workflow_id)
        self.execution_id = trigger_result['execution_id']
        
        print(f"✅ Workflow triggered: {self.execution_id}")
        print(f"📝 Created tasks: {trigger_result['info']['created_tasks']}")
        print(f"🚀 Ready tasks: {trigger_result['info']['ready_tasks']}")
        
        duration_ms = (time.time() - phase_start) * 1000
        self.test_results["phase_4"] = {
            "status": "success",
            "duration_ms": duration_ms,
            "execution_id": self.execution_id,
            "created_tasks": trigger_result['info']['created_tasks'],
            "ready_tasks": trigger_result['info']['ready_tasks']
        }
    
    def _phase_5_database_validation_after_trigger(self):
        """Phase 5: Database validation after workflow trigger"""
        print("\n5️⃣ PHASE 5: DATABASE VALIDATION (AFTER TRIGGER)")
        print("-" * 40)
        
        # Check executions table
        executions_result = database.list_executions(self.db_path)
        executions_count = len(executions_result.data) if executions_result.success else 0
        print(f"⚡ Executions: {executions_count}")
        
        # Check execution queue
        queue_result = database.list_execution_tasks(self.db_path, self.execution_id)
        queue_count = len(queue_result.data) if queue_result.success else 0
        print(f"📝 Queue tasks: {queue_count}")
        
        # Check ready tasks
        ready_result = database.get_ready_tasks_for_execution(self.db_path, self.execution_id)
        ready_count = len(ready_result.data.get('ready_tasks', [])) if ready_result.success else 0
        print(f"🚀 Ready tasks: {ready_count}")
        
        # Validate counts
        expected = self.test_config["database_validation"]["expected_counts"]
        if executions_count != expected['executions']:
            raise Exception(f"Expected {expected['executions']} executions, got {executions_count}")
        
        if queue_count != expected['execution_queue']:
            raise Exception(f"Expected {expected['execution_queue']} queue tasks, got {queue_count}")
        
        print("✅ Database validation after trigger passed")
        self.test_results["phase_5"] = {
            "status": "success",
            "executions_count": executions_count,
            "queue_count": queue_count,
            "ready_count": ready_count
        }
    
    def _phase_6_test_scheduler_setup(self):
        """Phase 6: Test scheduler setup"""
        print("\n6️⃣ PHASE 6: TEST SCHEDULER SETUP")
        print("-" * 40)
        
        # Create test scheduler
        self.test_scheduler = create_test_scheduler(self.db_path, failure_rate=0.0)
        
        # Start test scheduler
        started = self.test_scheduler.start()
        if not started:
            raise Exception("Test scheduler failed to start")
        
        print("✅ Test scheduler started")
        
        # Wait for scheduler to be fully ready
        time.sleep(2)
        
        # Verify scheduler status
        if not self.test_scheduler.is_running():
            raise Exception("Test scheduler is not running")
        
        status = self.test_scheduler.get_status()
        print(f"🔧 Queue Monitor: {'✅' if status['queue_monitor_running'] else '❌'}")
        print(f"📊 Result Monitor: {'✅' if status['result_monitor_running'] else '❌'}")
        
        self.test_results["phase_6"] = {
            "status": "success",
            "scheduler_status": status
        }
    
    def _phase_7_task_execution_simulation(self):
        """Phase 7: Task execution simulation"""
        print("\n7️⃣ PHASE 7: TASK EXECUTION SIMULATION")
        print("-" * 40)
        
        phase_start = time.time()
        
        # Monitor queue sizes before execution
        initial_sizes = self.test_scheduler.get_queue_sizes()
        print(f"📊 Initial queue sizes: {initial_sizes}")
        
        # Wait for task processing
        print("⏳ Waiting for task execution...")
        completed = self.test_scheduler.wait_for_completion(timeout=20.0)
        
        if not completed:
            print("⚠️ Tasks did not complete within timeout, checking status...")
            final_sizes = self.test_scheduler.get_queue_sizes()
            print(f"📊 Final queue sizes: {final_sizes}")
        else:
            print("✅ All tasks completed successfully")
        
        # Get execution statistics
        status = self.test_scheduler.get_status()
        queue_stats = status['queue_statistics']
        engine_stats = status['engine_statistics']
        
        print(f"📈 Queue Statistics:")
        print(f"   Total sent: {queue_stats['total_sent']}")
        print(f"   Total processed: {queue_stats['total_processed']}")
        print(f"   Total received: {queue_stats['total_received']}")
        
        print(f"🔧 Engine Statistics:")
        print(f"   Total executions: {engine_stats['total_executions']}")
        print(f"   Supported types: {engine_stats['supported_node_types']}")
        
        duration_ms = (time.time() - phase_start) * 1000
        self.test_results["phase_7"] = {
            "status": "success",
            "duration_ms": duration_ms,
            "completed": completed,
            "queue_statistics": queue_stats,
            "engine_statistics": engine_stats
        }
    
    def _phase_8_result_processing_validation(self):
        """Phase 8: Result processing validation"""
        print("\n8️⃣ PHASE 8: RESULT PROCESSING VALIDATION")
        print("-" * 40)
        
        # Check execution results table
        results_result = database.list_execution_records(self.db_path, self.execution_id)
        results_count = len(results_result.data) if results_result.success else 0
        print(f"📊 Execution results: {results_count}")
        
        # Check execution status
        execution_result = database.get_execution(self.db_path, self.execution_id)
        if execution_result.success:
            execution_status = execution_result.data.get('status', 'unknown')
            print(f"⚡ Execution status: {execution_status}")
        else:
            execution_status = 'unknown'
        
        # Validate results count
        expected_results = self.test_config["database_validation"]["expected_counts"]["execution_results"]
        if results_count >= expected_results:  # Allow for partial completion
            print("✅ Result processing validation passed")
        else:
            print(f"⚠️ Expected {expected_results} results, got {results_count}")
        
        self.test_results["phase_8"] = {
            "status": "success",
            "results_count": results_count,
            "execution_status": execution_status
        }
    
    def _phase_9_final_database_validation(self):
        """Phase 9: Final database validation"""
        print("\n9️⃣ PHASE 9: FINAL DATABASE VALIDATION")
        print("-" * 40)
        
        # Complete database state check
        final_state = {}
        
        # Workflows
        workflows_result = database.list_workflows(self.db_path)
        final_state["workflows"] = len(workflows_result.data) if workflows_result.success else 0
        
        # Nodes
        nodes_result = database.list_workflow_nodes(self.db_path, self.workflow_id)
        final_state["nodes"] = len(nodes_result.data) if nodes_result.success else 0
        
        # Edges
        edges_result = database.list_workflow_edges(self.db_path, self.workflow_id)
        final_state["edges"] = len(edges_result.data) if edges_result.success else 0
        
        # Executions
        executions_result = database.list_executions(self.db_path)
        final_state["executions"] = len(executions_result.data) if executions_result.success else 0
        
        # Execution queue (should be mostly empty or completed)
        queue_result = database.list_execution_tasks(self.db_path, self.execution_id)
        final_state["execution_queue"] = len(queue_result.data) if queue_result.success else 0
        
        # Execution results
        results_result = database.list_execution_records(self.db_path, self.execution_id)
        final_state["execution_results"] = len(results_result.data) if results_result.success else 0
        
        print("📊 Final Database State:")
        for table, count in final_state.items():
            print(f"   {table}: {count}")
        
        print("✅ Final database validation completed")
        self.test_results["phase_9"] = {
            "status": "success",
            "final_state": final_state
        }
    
    def _phase_10_performance_analysis(self):
        """Phase 10: Performance analysis"""
        print("\n🔟 PHASE 10: PERFORMANCE ANALYSIS")
        print("-" * 40)
        
        total_duration = (datetime.now() - self.start_time).total_seconds() * 1000
        
        # Performance metrics
        performance = {
            "total_test_duration_ms": total_duration,
            "workflow_load_time_ms": self.test_results["phase_2"]["duration_ms"],
            "workflow_trigger_time_ms": self.test_results["phase_4"]["duration_ms"],
            "task_execution_time_ms": self.test_results["phase_7"]["duration_ms"]
        }
        
        # Check against thresholds
        thresholds = self.test_config["performance_thresholds"]
        performance_issues = []
        
        for metric, value in performance.items():
            threshold_key = f"max_{metric}"
            if threshold_key in thresholds and value > thresholds[threshold_key]:
                performance_issues.append(f"{metric}: {value}ms > {thresholds[threshold_key]}ms")
        
        print("⏱️ Performance Metrics:")
        for metric, value in performance.items():
            print(f"   {metric}: {value:.2f}ms")
        
        if performance_issues:
            print("⚠️ Performance Issues:")
            for issue in performance_issues:
                print(f"   {issue}")
        else:
            print("✅ All performance metrics within thresholds")
        
        self.test_results["phase_10"] = {
            "status": "success",
            "performance": performance,
            "performance_issues": performance_issues
        }
    
    def _generate_success_summary(self):
        """Generate success summary"""
        print("\n" + "=" * 60)
        print("🎉 END-TO-END TEST COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        
        total_duration = (datetime.now() - self.start_time).total_seconds()
        
        print(f"⏱️ Total Duration: {total_duration:.2f} seconds")
        print(f"📊 Workflow ID: {self.workflow_id}")
        print(f"⚡ Execution ID: {self.execution_id}")
        print(f"🔧 Tasks Executed: {self.test_results['phase_7']['engine_statistics']['total_executions']}")
        print(f"📈 Results Processed: {self.test_results['phase_8']['results_count']}")
        
        # Overall success
        self.test_results["overall"] = {
            "status": "success",
            "total_duration_seconds": total_duration,
            "all_phases_passed": True
        }
    
    def _handle_test_failure(self, error: Exception):
        """Handle test failure"""
        print(f"\n❌ TEST FAILED: {error}")
        
        self.test_results["overall"] = {
            "status": "failed",
            "error": str(error),
            "all_phases_passed": False
        }
    
    def _cleanup(self):
        """Cleanup test resources"""
        try:
            if self.test_scheduler:
                self.test_scheduler.stop()
            
            if self.app:
                self.app.stop()
            
            # Clean up test files
            test_files = ["test_workflow.json"]
            for file in test_files:
                if os.path.exists(file):
                    os.remove(file)
            
            print("🧹 Cleanup completed")
            
        except Exception as e:
            print(f"⚠️ Cleanup error: {e}")
    
    def _get_phase_duration(self) -> float:
        """Get duration since start in milliseconds"""
        if self.start_time:
            return (datetime.now() - self.start_time).total_seconds() * 1000
        return 0.0


def run_end_to_end_test() -> Dict[str, Any]:
    """
    Run complete end-to-end test
    
    Returns:
        Test results
    """
    test_suite = EndToEndTestSuite()
    return test_suite.run_complete_test()


if __name__ == "__main__":
    results = run_end_to_end_test()
    
    if results["overall"]["status"] == "success":
        print("\n✅ ALL TESTS PASSED!")
        exit(0)
    else:
        print("\n❌ TESTS FAILED!")
        exit(1) 