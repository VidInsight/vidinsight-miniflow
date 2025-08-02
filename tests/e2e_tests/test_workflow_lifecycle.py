"""
TEST WORKFLOW LIFECYCLE E2E
==========================

End-to-end workflow yaşam döngüsü testleri.
"""

import pytest
import time
from miniflow.main import MiniflowCore


class TestWorkflowLifecycleE2E:
    """Workflow yaşam döngüsü E2E testleri"""
    
    @pytest.mark.e2e
    def test_complete_workflow_lifecycle(self):
        """Tam workflow yaşam döngüsü testi"""
        # Initialize core with scheduler enabled
        core = MiniflowCore(
            db_type="sqlite",
            enable_scheduler=True,
            db_name="e2e_test.db"
        )
        
        try:
            # Start core
            core.start()
            
            # Create test script
            script_data = {
                "name": "e2e_test_script",
                "description": "E2E test script",
                "input_params": {"input1": "string"},
                "output_params": {"result": "string"}
            }
            
            script_content = '''
def main(input1: str) -> dict:
    """E2E test script"""
    result = f"Processed: {input1}"
    return {"result": result, "status": "success"}
'''
            
            script_result = core.script_create(script_data, script_content)
            script_id = script_result["script_id"]
            
            # Create test workflow
            workflow_data = {
                "name": "e2e_test_workflow",
                "description": "E2E test workflow",
                "status": "active",
                "priority": 1,
                "nodes": [
                    {
                        "name": "test_node",
                        "script_id": script_id,
                        "params": {"input1": "test_value"},
                        "max_retries": 3,
                        "timeout_seconds": 300
                    }
                ],
                "edges": []
            }
            
            workflow_result = core.workflow_create(workflow_data)
            workflow_id = workflow_result["workflow_id"]
            
            # Trigger workflow
            execution_result = core.trigger_workflow(workflow_id)
            execution_id = execution_result["execution_id"]
            
            # Wait for execution to complete
            max_wait = 30  # seconds
            wait_time = 0
            
            while wait_time < max_wait:
                execution = core.execution_get(execution_id)
                if execution["status"] in ["completed", "failed"]:
                    break
                time.sleep(1)
                wait_time += 1
            
            # Verify execution completed
            final_execution = core.execution_get(execution_id)
            assert final_execution["status"] in ["completed", "failed"]
            
            # Cleanup
            core.workflow_delete(workflow_id)
            core.script_delete(script_id)
            
        finally:
            core.stop()
            
    @pytest.mark.e2e
    def test_workflow_with_multiple_nodes(self):
        """Çoklu node'lu workflow testi"""
        core = MiniflowCore(
            db_type="sqlite",
            enable_scheduler=True,
            db_name="e2e_multi_node.db"
        )
        
        try:
            core.start()
            
            # Create multiple scripts
            scripts = []
            for i in range(3):
                script_data = {
                    "name": f"e2e_script_{i}",
                    "description": f"E2E script {i}",
                    "input_params": {"input": "string"},
                    "output_params": {"result": "string"}
                }
                
                script_content = f'''
def main(input: str) -> dict:
    """E2E script {i}"""
    result = f"Node {{i}}: {{input}}"
    return {{"result": result, "status": "success"}}
'''
                
                script_result = core.script_create(script_data, script_content)
                scripts.append(script_result["script_id"])
            
            # Create workflow with multiple nodes
            workflow_data = {
                "name": "e2e_multi_node_workflow",
                "description": "Multi-node E2E workflow",
                "status": "active",
                "priority": 1,
                "nodes": [
                    {
                        "name": f"node_{i}",
                        "script_id": script_id,
                        "params": {"input": f"test_input_{i}"},
                        "max_retries": 2,
                        "timeout_seconds": 200
                    }
                    for i, script_id in enumerate(scripts)
                ],
                "edges": [
                    {
                        "from_node_id": f"node_{i}",
                        "to_node_id": f"node_{i+1}",
                        "condition_type": "success"
                    }
                    for i in range(len(scripts) - 1)
                ]
            }
            
            workflow_result = core.workflow_create(workflow_data)
            workflow_id = workflow_result["workflow_id"]
            
            # Trigger and monitor
            execution_result = core.trigger_workflow(workflow_id)
            execution_id = execution_result["execution_id"]
            
            # Wait for completion
            max_wait = 60
            wait_time = 0
            
            while wait_time < max_wait:
                execution = core.execution_get(execution_id)
                if execution["status"] in ["completed", "failed"]:
                    break
                time.sleep(2)
                wait_time += 2
            
            # Verify completion
            final_execution = core.execution_get(execution_id)
            assert final_execution["status"] in ["completed", "failed"]
            
            # Cleanup
            core.workflow_delete(workflow_id)
            for script_id in scripts:
                core.script_delete(script_id)
                
        finally:
            core.stop()
