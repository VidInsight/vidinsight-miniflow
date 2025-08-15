import pytest

from miniflow.database.models import Script, ScriptType, ScriptTestStatus
from miniflow.exceptions import CRUDException, ValidationError


@pytest.fixture
def sample_script_data():
    """Test için sample script data"""
    return {
        "name": "test_script",
        "description": "Test script description",
        "language": ScriptType.PYTHON,
        "script_path": "/scripts/data_processor.py",
        "input_params": {
            "input_file": "string",
            "max_rows": 1000,
            "verbose": True
        },
        "output_params": {
            "output_file": "string",
            "row_count": "integer",
            "summary": "string"
        }
    }


@pytest.fixture
def invalid_script_data():
    """Test için invalid script data"""
    return {
        "name": "test_script",
        "description": "Test script description",
        "language": ScriptType.PYTHON,
        "script_path": "/scripts/data_processor.py",
        "input_params": {
            "input_file": "string",
            "max_rows": 1000,
            "verbose": True
        },
        "output_params": {
            "output_file": "string",
            "row_count": "integer",
            "summary": "string"
        },
        "random_col": 4
    }


@pytest.fixture
def multiple_script_data():
    """Multiple script data for bulk operations"""
    return [
        {
            "name": "script_1",
            "description": "First script processing data",
            "language": ScriptType.PYTHON,
            "script_path": "/scripts/script1.py",
            "input_params": {"param1": "value1"},
            "output_params": {"result": "output1"}
        },
        {
            "name": "script_2",
            "description": "Second script for cleanup",
            "language": ScriptType.PYTHON,
            "script_path": "/scripts/cleanup.sh",
            "input_params": {"cleanup_level": 2},
            "output_params": {"status": "success"}
        },
        {
            "name": "script_3",
            "description": "Third script in JavaScript",
            "language": ScriptType.PYTHON,
            "script_path": "/scripts/script3.js",
            "input_params": {"threshold": 0.8},
            "output_params": {"alert_count": 5}
        }
    ]


@pytest.mark.unittest
class TestScriptCrudBasic:
    """Temel CRUD işlemleri testleri"""
    def test_script_crud_initialization(self, script_crud):
        assert script_crud.model == Script
        assert script_crud.model_name == "Script"

    def test_create_script_valid_data(self, clean_db, script_crud, sample_script_data):
        script = script_crud.create_script(clean_db, **sample_script_data)

        assert script is not None
        assert script.id is not None
        assert script.id.startswith("SC-")
        assert script.created_at is not None
        assert script.updated_at is not None
        assert script.name == "test_script"
        assert script.description == "Test script description"
        assert script.language == ScriptType.PYTHON
        assert script.script_path == "/scripts/data_processor.py"
        assert script.input_params == {
            "input_file": "string",
            "max_rows": 1000,
            "verbose": True
        }
        assert script.output_params == {
            "output_file": "string",
            "row_count": "integer",
            "summary": "string"
        }
        assert script.test_status == ScriptTestStatus.UNTESTED

    def test_create_script_invalid_data(self, clean_db, script_crud, invalid_script_data):
        """Geçersiz alanlar ile script oluşturma testi - geçersiz alanlar filtrelenir"""
        script = script_crud.create_script(clean_db, **invalid_script_data)

        assert script is not None
        assert script.id is not None
        assert script.id.startswith("SC-")
        assert script.created_at is not None
        assert script.updated_at is not None
        assert script.name == "test_script"
        assert script.description == "Test script description"
        assert script.language == ScriptType.PYTHON
        assert script.script_path == "/scripts/data_processor.py"
        assert script.input_params == {
            "input_file": "string",
            "max_rows": 1000,
            "verbose": True
        }
        assert script.output_params == {
            "output_file": "string",
            "row_count": "integer",
            "summary": "string"
        }
        
        # Geçersiz alanın filtrelendiğini doğrula
        assert not hasattr(script, 'random_col')

    def test_update_script_valid_data(self, clean_db, script_crud, sample_script_data):
        script = script_crud.create_script(clean_db, **sample_script_data)

        update_payload = {
            "description": "Updated description",
            "script_path": "/scripts/updated_script.py",
            "input_params": {"new_param": "new_value"},
            "output_params": {"new_output": "new_result"}
        }

        updated_script = script_crud.update_script(clean_db, script.id, **update_payload)

        assert updated_script.id == script.id
        assert updated_script.name == script.name
        assert updated_script.description == "Updated description"
        assert updated_script.script_path == "/scripts/updated_script.py"
        assert updated_script.input_params == {"new_param": "new_value"}
        assert updated_script.output_params == {"new_output": "new_result"}
        assert updated_script.updated_at != script.created_at

    def test_update_script_invalid_data(self, clean_db, script_crud, sample_script_data):
        script = script_crud.create_script(clean_db, **sample_script_data)

        invalid_update_payload = {
            "description": "Updated description",
            "random_field": "invalid_value"
        }

        updated_script = script_crud.update_script(clean_db, script.id, **invalid_update_payload)

        assert updated_script.id == script.id
        assert updated_script.description == "Updated description"
        # Geçersiz alanın filtrelendiğini doğrula
        assert not hasattr(updated_script, 'random_field')

    def test_update_script_invalid_id(self, clean_db, script_crud, sample_script_data):
        """Geçersiz ID ile script güncelleme testi"""
        with pytest.raises(CRUDException, match="No such record SC-INVALID"):
            script_crud.update_script(clean_db, "SC-INVALID", description="Updated")

    def test_delete_script_valid_id(self, clean_db, script_crud, sample_script_data):
        script = script_crud.create_script(clean_db, **sample_script_data)
        
        deleted_script = script_crud.delete_script(clean_db, script.id)
        
        assert deleted_script.id == script.id
        assert deleted_script.name == script.name
        
        # Script'in gerçekten silindiğini doğrula
        with pytest.raises(CRUDException, match=f"No such record {script.id}"):
            script_crud.find_by_id(clean_db, script.id)

    def test_delete_script_invalid_id(self, clean_db, script_crud):
        """Geçersiz ID ile script silme testi"""
        with pytest.raises(CRUDException, match="No such record SC-INVALID"):
            script_crud.delete_script(clean_db, "SC-INVALID")

    def test_find_by_id_valid(self, clean_db, script_crud, sample_script_data):
        script = script_crud.create_script(clean_db, **sample_script_data)
        
        found_script = script_crud.find_by_id(clean_db, script.id)
        
        assert found_script is not None
        assert found_script.id == script.id
        assert found_script.name == script.name

    def test_find_by_id_invalid(self, clean_db, script_crud):
        """Geçersiz ID ile script bulma testi"""
        with pytest.raises(CRUDException, match="No such record SC-INVALID"):
            script_crud.find_by_id(clean_db, "SC-INVALID")

@pytest.mark.unittest
class TestScriptCrudBusinessLogic:
    """İş mantığı testleri"""
    pass