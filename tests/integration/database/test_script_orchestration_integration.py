"""
Integration tests for ScriptOrchestrator with ScriptCRUD
Tests the complete flow from orchestration layer to database and file system
"""

import pytest
import os
import tempfile
from pathlib import Path

from miniflow.database.orchestration.script_orchestration import ScriptOrchestrator
from miniflow.exceptions import ValidationError, BusinessLogicError, ResourceError
from miniflow.database.models import Script, ScriptTestStatus


@pytest.fixture
def script_orchestrator():
    """ Real ScriptOrchestrator instance """
    return ScriptOrchestrator()

@pytest.fixture
def temp_script_path():
    """ Temporary directory for script files """
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir

@pytest.fixture
def sample_script_data():
    """ Sample script data for testing """
    return {
        'name': 'test_script',
        'description': 'Integration test script',
        'script_content': '''#!/usr/bin/env python3
# Test script for integration testing
import sys

def main():
    print("Hello from test script!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
''',
        'input_params': {'param1': 'string', 'param2': 'int'},
        'output_params': {'result': 'string'}
    }

@pytest.fixture
def invalid_script_data():
    """ Invalid script data for testing """
    return {
        'name': 'test@script!',  # Invalid characters
        'description': 'Invalid script',
        'script_content': 'print("test")',
        'invalid_field': 'should_be_ignored'
    }

@pytest.fixture
def missing_script_data():
    """ Missing required fields """
    return {
        'description': 'Script without name',
        'script_content': 'print("test")'
    }

@pytest.fixture
def sample_script_data_batch():
    """ Sample script data batch for testing """
    return [
        {
            'name': 'script_python_1',
            'description': 'First Python script',
            'script_content': 'print("Python 1")',
            'language': 'py'
        },
        {
            'name': 'script_python_2', 
            'description': 'Second Python script',
            'script_content': 'import os\nprint("Python 2")',
            'language': 'py'
        },
        {
            'name': 'script_bash_1',
            'description': 'First Bash script',
            'script_content': '#!/bin/bash\necho "Bash script"',
            'language': 'sh'
        }
    ]


@pytest.mark.integration
class TestScriptOrchestrationCreate:
    def test_create_script_with_valid_data(self, clean_db, script_orchestrator, temp_script_path, sample_script_data):
        result = script_orchestrator.create(clean_db, temp_script_path, sample_script_data)

        # Verify the result
        assert isinstance(result, dict)
        assert result is not None
        assert 'id' in result
        assert result['name'] == sample_script_data['name']
        assert result['description'] == sample_script_data['description']
        assert result['language'] == 'py'
        assert result['script_path'].endswith('.py')
        assert 'input_params' in result
        assert 'output_params' in result
        assert result['test_status'] == ScriptTestStatus.UNTESTED

        # Verify the database
        script = clean_db.get(Script, result['id'])
        assert script is not None
        assert script.name == sample_script_data['name']
        assert script.description == sample_script_data['description']

        # Verify the file was created
        assert os.path.exists(result['script_path'])
        with open(result['script_path'], 'r') as f:
            content = f.read()
            assert content == sample_script_data['script_content']

    def test_create_script_with_duplicate_name(self, clean_db, script_orchestrator, temp_script_path, sample_script_data):
        # Create first script
        script_orchestrator.create(clean_db, temp_script_path, sample_script_data)

        # Try to create second script with same name
        with pytest.raises(ValidationError, match="Script with name 'test_script' already exists"):
            script_orchestrator.create(clean_db, temp_script_path, sample_script_data)

    def test_create_script_with_invalid_name(self, clean_db, script_orchestrator, temp_script_path, invalid_script_data):
        with pytest.raises(ValidationError, match="Script name must contain only alphanumeric characters"):
            script_orchestrator.create(clean_db, temp_script_path, invalid_script_data)

    def test_create_script_with_missing_name(self, clean_db, script_orchestrator, temp_script_path, missing_script_data):
        with pytest.raises(ValidationError, match="Script name is required"):
            script_orchestrator.create(clean_db, temp_script_path, missing_script_data)

    def test_create_script_language_detection(self, clean_db, script_orchestrator, temp_script_path):
        # Test Python detection
        python_data = {
            'name': 'python_script',
            'script_content': 'import os\ndef hello():\n    print("Hello")'
        }
        result = script_orchestrator.create(clean_db, temp_script_path, python_data)
        assert result['language'] == 'py'
        assert result['script_path'].endswith('.py')

        # Test Bash detection
        bash_data = {
            'name': 'bash_script',
            'script_content': '#!/bin/bash\necho "Hello"'
        }
        result = script_orchestrator.create(clean_db, temp_script_path, bash_data)
        assert result['language'] == 'sh'
        assert result['script_path'].endswith('.sh')

    def test_create_script_file_write_error(self, clean_db, script_orchestrator, sample_script_data):
        # Use invalid path to trigger file write error
        invalid_path = "/invalid/nonexistent/path"
        
        with pytest.raises(ResourceError, match="Failed to write script file"):
            script_orchestrator.create(clean_db, invalid_path, sample_script_data)

    def test_create_script_file_already_exists(self, clean_db, script_orchestrator, temp_script_path, sample_script_data):
        # Manually create a file with the same name that would be created
        script_name = sample_script_data['name']
        file_path = os.path.join(temp_script_path, f"{script_name}.py")
        
        # Create the file manually
        with open(file_path, 'w') as f:
            f.write("# Existing file")
        
        # Now try to create script - should fail because file already exists
        with pytest.raises(ResourceError, match="Script file already exists at path"):
            script_orchestrator.create(clean_db, temp_script_path, sample_script_data)


@pytest.mark.integration
class TestScriptOrchestrationUpdate:
    def test_update_script_with_valid_data(self, clean_db, script_orchestrator, temp_script_path, sample_script_data):
        # Create script first
        script = script_orchestrator.create(clean_db, temp_script_path, sample_script_data)

        update_data = {
            'description': 'Updated description via orchestration',
            'script_content': 'print("Updated content")'
        }

        updated_script = script_orchestrator.update(clean_db, temp_script_path, script['id'], update_data)

        assert updated_script is not None
        assert updated_script['id'] == script['id']
        assert updated_script['description'] == update_data['description']

        # Verify file content was updated
        with open(updated_script['script_path'], 'r') as f:
            content = f.read()
            assert content == update_data['script_content']

    def test_update_script_with_new_name(self, clean_db, script_orchestrator, temp_script_path, sample_script_data):
        # Create script first
        script = script_orchestrator.create(clean_db, temp_script_path, sample_script_data)
        old_path = script['script_path']

        update_data = {'name': 'renamed_script'}
        updated_script = script_orchestrator.update(clean_db, temp_script_path, script['id'], update_data)

        assert updated_script['name'] == 'renamed_script'
        assert updated_script['script_path'] != old_path
        assert updated_script['script_path'].endswith('renamed_script.py')

        # Verify old file was renamed
        assert not os.path.exists(old_path)
        assert os.path.exists(updated_script['script_path'])

    def test_update_script_with_invalid_id(self, clean_db, script_orchestrator, temp_script_path):
        with pytest.raises(BusinessLogicError, match="Script not found: SC-INVALID"):
            script_orchestrator.update(clean_db, temp_script_path, 'SC-INVALID', {'name': 'test'})

    def test_update_script_with_duplicate_name(self, clean_db, script_orchestrator, temp_script_path, sample_script_data):
        # Create two scripts
        script1 = script_orchestrator.create(clean_db, temp_script_path, sample_script_data)
        
        script2_data = sample_script_data.copy()
        script2_data['name'] = 'second_script'
        script2 = script_orchestrator.create(clean_db, temp_script_path, script2_data)

        # Try to rename script2 to script1's name
        with pytest.raises(ValidationError, match="Script with name 'test_script' already exists"):
            script_orchestrator.update(clean_db, temp_script_path, script2['id'], {'name': script1['name']})

    def test_update_script_file_permission_error(self, clean_db, script_orchestrator, temp_script_path, sample_script_data):
        # Create script
        script = script_orchestrator.create(clean_db, temp_script_path, sample_script_data)
        
        # Make file read-only to simulate permission error
        os.chmod(script['script_path'], 0o444)
        
        try:
            # Try to update content - should raise ResourceError
            with pytest.raises(ResourceError, match="Failed to update script file"):
                script_orchestrator.update(clean_db, temp_script_path, script['id'], {
                    'script_content': 'new content'
                })
        finally:
            # Restore permissions for cleanup
            os.chmod(script['script_path'], 0o644)

    def test_update_script_rename_to_existing_file(self, clean_db, script_orchestrator, temp_script_path, sample_script_data):
        # Create a script
        script_data = sample_script_data.copy()
        script_data['name'] = 'original_script'
        script = script_orchestrator.create(clean_db, temp_script_path, script_data)
        
        # Manually create a file with the target name
        target_file_path = os.path.join(temp_script_path, "target_script.py")
        with open(target_file_path, 'w') as f:
            f.write("# Existing target file")
        
        # Try to rename script to the existing file name - should fail due to file conflict
        with pytest.raises(ResourceError, match="Script file already exists at path"):
            script_orchestrator.update(clean_db, temp_script_path, script['id'], {'name': 'target_script'})

    def test_update_script_language_change_to_existing_file(self, clean_db, script_orchestrator, temp_script_path):
        # Create a Python script
        python_script_data = {
            'name': 'test_script',
            'script_content': 'print("Python script")',
            'language': 'py'
        }
        script = script_orchestrator.create(clean_db, temp_script_path, python_script_data)
        
        # Manually create a bash file with the same name
        bash_file_path = os.path.join(temp_script_path, 'test_script.sh')
        with open(bash_file_path, 'w') as f:
            f.write('echo "existing bash script"')
        
        # Try to update script content to bash - should fail due to file conflict
        with pytest.raises(ResourceError, match="Script file already exists at path"):
            script_orchestrator.update(clean_db, temp_script_path, script['id'], {
                'script_content': '#!/bin/bash\necho "New bash script"'
            })


@pytest.mark.integration
class TestScriptOrchestrationDelete:
    def test_delete_script_with_valid_id(self, clean_db, script_orchestrator, temp_script_path, sample_script_data):
        script = script_orchestrator.create(clean_db, temp_script_path, sample_script_data)
        script_path = script['script_path']

        deleted_script = script_orchestrator.delete(clean_db, script['id'])

        assert deleted_script is not None
        assert deleted_script['id'] == script['id']
        assert 'affected_nodes' in deleted_script
        assert 'affected_workflows' in deleted_script

        # Verify file was deleted
        assert not os.path.exists(script_path)

        # Verify database record was deleted
        db_script = clean_db.get(Script, script['id'])
        assert db_script is None

    def test_delete_script_with_invalid_id(self, clean_db, script_orchestrator):
        with pytest.raises(BusinessLogicError, match="Script not found: SC-INVALID"):
            script_orchestrator.delete(clean_db, 'SC-INVALID')

    def test_delete_script_in_use_without_force(self, clean_db, script_orchestrator, temp_script_path, sample_script_data):
        # Create script
        script = script_orchestrator.create(clean_db, temp_script_path, sample_script_data)
        
        # Create a workflow and node that uses this script
        from miniflow.database.models import Workflow, Node
        
        # Create workflow
        workflow = Workflow(name="test_workflow", description="Test workflow")
        clean_db.add(workflow)
        clean_db.flush()
        
        # Create node with script
        node = Node(
            workflow_id=workflow.id,
            script_id=script['id'],
            name="test_node",
            description="Test node"
        )
        clean_db.add(node)
        clean_db.commit()
        
        # Try to delete script without force - should fail
        with pytest.raises(BusinessLogicError, match="Cannot delete script - it is being used by 1 node\\(s\\). Use force=True to override."):
            script_orchestrator.delete(clean_db, script['id'], force=False)

    def test_delete_script_in_use_with_force(self, clean_db, script_orchestrator, temp_script_path, sample_script_data):
        # Create script
        script = script_orchestrator.create(clean_db, temp_script_path, sample_script_data)
        
        # Create a workflow and node that uses this script
        from miniflow.database.models import Workflow, Node, WorkflowStatus
        
        # Create workflow
        workflow = Workflow(name="test_workflow", description="Test workflow", status=WorkflowStatus.ACTIVE)
        clean_db.add(workflow)
        clean_db.flush()
        
        # Create node with script
        node = Node(
            workflow_id=workflow.id,
            script_id=script['id'],
            name="test_node",
            description="Test node"
        )
        clean_db.add(node)
        clean_db.commit()
        
        # Delete script with force - should succeed
        result = script_orchestrator.delete(clean_db, script['id'], force=True)
        
        assert result is not None
        assert result['affected_nodes'] == 1
        assert result['affected_workflows'] == 1
        
        # Verify workflow status changed to DRAFT
        clean_db.refresh(workflow)
        assert workflow.status == WorkflowStatus.DRAFT


@pytest.mark.integration
class TestScriptOrchestrationSearch:
    def test_search_script_with_one_criteria(self, clean_db, script_orchestrator, temp_script_path, sample_script_data_batch):
        # Create scripts
        for script_data in sample_script_data_batch:
            script_orchestrator.create(clean_db, temp_script_path, script_data)

        # Search by language
        search_result = script_orchestrator.search(clean_db, {'language': 'py'})

        assert search_result['total_count'] == 2
        assert len(search_result['data']) == 2
        assert all(script['language'] == 'py' for script in search_result['data'])

    def test_search_script_with_invalid_criteria(self, clean_db, script_orchestrator, temp_script_path, sample_script_data):
        script_orchestrator.create(clean_db, temp_script_path, sample_script_data)

        with pytest.raises(ValueError, match="Field 'invalid_field' does not exist in Script"):
            script_orchestrator.search(clean_db, {'invalid_field': 'value'})


@pytest.mark.integration
class TestScriptOrchestrationGet:
    def test_get_script_with_valid_id(self, clean_db, script_orchestrator, temp_script_path, sample_script_data):
        script = script_orchestrator.create(clean_db, temp_script_path, sample_script_data)

        result = script_orchestrator.get(clean_db, script['id'], include_content=False)

        assert result is not None
        assert result['id'] == script['id']
        assert result['name'] == sample_script_data['name']
        assert 'script_content' not in result

    def test_get_script_with_content(self, clean_db, script_orchestrator, temp_script_path, sample_script_data):
        script = script_orchestrator.create(clean_db, temp_script_path, sample_script_data)

        result = script_orchestrator.get(clean_db, script['id'], include_content=True)

        assert result is not None
        assert 'script_content' in result
        assert result['script_content'] == sample_script_data['script_content']

    def test_get_script_with_invalid_id(self, clean_db, script_orchestrator):
        with pytest.raises(BusinessLogicError, match="Script not found: SC-INVALID"):
            script_orchestrator.get(clean_db, 'SC-INVALID')

    def test_get_script_with_missing_file(self, clean_db, script_orchestrator, temp_script_path, sample_script_data):
        # Create script
        script = script_orchestrator.create(clean_db, temp_script_path, sample_script_data)
        
        # Delete the physical file but keep database record
        os.remove(script['script_path'])
        
        # Try to get with content - should raise ResourceError
        with pytest.raises(ResourceError, match="Script file not found"):
            script_orchestrator.get(clean_db, script['id'], include_content=True)
        
        # Should work fine without content
        result = script_orchestrator.get(clean_db, script['id'], include_content=False)
        assert result is not None
        assert 'script_content' not in result

    def test_get_script_with_missing_script_path(self, clean_db, script_orchestrator, temp_script_path, sample_script_data):
        # Create script
        script = script_orchestrator.create(clean_db, temp_script_path, sample_script_data)
        
        # Manually set empty script_path in database (since NULL is not allowed)
        from miniflow.database.models import Script
        db_script = clean_db.get(Script, script['id'])
        db_script.script_path = ""
        clean_db.commit()
        
        # Try to get with content - should raise ResourceError
        with pytest.raises(ResourceError, match="Script file path is missing"):
            script_orchestrator.get(clean_db, script['id'], include_content=True)


@pytest.mark.integration
class TestScriptOrchestrationExtraOperations:
    def test_count_scripts(self, clean_db, script_orchestrator, temp_script_path, sample_script_data_batch):
        # Initially should be 0
        initial_count = script_orchestrator.count(clean_db)
        assert initial_count == 0

        # Create scripts
        for script_data in sample_script_data_batch:
            script_orchestrator.create(clean_db, temp_script_path, script_data)

        # Count should match
        final_count = script_orchestrator.count(clean_db)
        assert final_count == len(sample_script_data_batch)

    def test_exists_script_with_valid_id(self, clean_db, script_orchestrator, temp_script_path, sample_script_data):
        script = script_orchestrator.create(clean_db, temp_script_path, sample_script_data)

        exists = script_orchestrator.exists(clean_db, script['id'])
        assert exists is True

    def test_exists_script_with_invalid_id(self, clean_db, script_orchestrator):
        exists = script_orchestrator.exists(clean_db, 'SC-NONEXISTENT')
        assert exists is False

    def test_get_by_language(self, clean_db, script_orchestrator, temp_script_path, sample_script_data_batch):
        # Create scripts
        for script_data in sample_script_data_batch:
            script_orchestrator.create(clean_db, temp_script_path, script_data)

        # Get Python scripts
        python_scripts = script_orchestrator.get_by_language(clean_db, 'py')
        assert len(python_scripts) == 2
        assert all(script['language'] == 'py' for script in python_scripts)

        # Get Bash scripts
        bash_scripts = script_orchestrator.get_by_language(clean_db, 'sh')
        assert len(bash_scripts) == 1
        assert bash_scripts[0]['language'] == 'sh'

    def test_get_untested_scripts(self, clean_db, script_orchestrator, temp_script_path, sample_script_data_batch):
        # Create scripts (all should be UNTESTED by default)
        for script_data in sample_script_data_batch:
            script_orchestrator.create(clean_db, temp_script_path, script_data)

        untested_scripts = script_orchestrator.get_untested_scripts(clean_db)
        assert len(untested_scripts) == len(sample_script_data_batch)
        assert all(script['test_status'] == ScriptTestStatus.UNTESTED for script in untested_scripts)

    def test_get_passed_scripts(self, clean_db, script_orchestrator, temp_script_path, sample_script_data):
        # Create script and manually update its test status to PASSED
        script = script_orchestrator.create(clean_db, temp_script_path, sample_script_data)
        
        # Update test status in database directly (since there's no orchestration method for this yet)
        db_script = clean_db.get(Script, script['id'])
        db_script.test_status = ScriptTestStatus.PASSED
        clean_db.commit()

        passed_scripts = script_orchestrator.get_passed_scripts(clean_db)
        assert len(passed_scripts) == 1
        assert passed_scripts[0]['test_status'] == ScriptTestStatus.PASSED

    def test_get_failed_scripts(self, clean_db, script_orchestrator, temp_script_path, sample_script_data):
        # Create script and manually update its test status to FAILED
        script = script_orchestrator.create(clean_db, temp_script_path, sample_script_data)
        
        # Update test status in database directly
        db_script = clean_db.get(Script, script['id'])
        db_script.test_status = ScriptTestStatus.FAILED
        clean_db.commit()

        failed_scripts = script_orchestrator.get_failed_scripts(clean_db)
        assert len(failed_scripts) == 1
        assert failed_scripts[0]['test_status'] == ScriptTestStatus.FAILED

    def test_get_all_scripts(self, clean_db, script_orchestrator, temp_script_path, sample_script_data_batch):
        # Create scripts
        for script_data in sample_script_data_batch:
            script_orchestrator.create(clean_db, temp_script_path, script_data)

        all_scripts = script_orchestrator.get_all_scripts(clean_db)
        assert len(all_scripts) == len(sample_script_data_batch)
        
        # Verify all scripts are returned as dicts
        for script in all_scripts:
            assert isinstance(script, dict)
            assert 'id' in script
            assert 'name' in script
            assert 'language' in script