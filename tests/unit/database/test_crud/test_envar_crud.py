import pytest

from miniflow.database.models import EnvironmentVariable
from miniflow.exceptions import CRUDException


@pytest.fixture
def sample_env_var_data():
    """Test için sample environment variable data"""
    return {
        "name": "TEST_VAR",
        "value": "test_value",
        "description": "Test environment variable",
        "is_encrypted": False
    }


@pytest.fixture
def invalid_env_var_data():
    """Test için invalid environment variable data"""
    return {
        "name": "TEST_VAR",
        "value": "test_value",
        "description": "Test environment variable",
        "is_encrypted": False,
        "random_col": 4
    }


@pytest.mark.unittest
class TestEnvarCrudBasic:
    """Temel CRUD işlemleri testleri"""
    
    def test_envar_crud_initialization(self, envar_crud):
        assert envar_crud.model == EnvironmentVariable
        assert envar_crud.model_name == "EnvironmentVariable"

    def test_create_env_var_valid_data(self, clean_db, envar_crud, sample_env_var_data):
        env_var = envar_crud.create_env_var(clean_db, **sample_env_var_data)

        assert env_var is not None
        assert env_var.id is not None
        assert env_var.id.startswith("EV-")
        assert env_var.created_at is not None
        assert env_var.updated_at is not None
        assert env_var.name == "TEST_VAR"
        assert env_var.value == "test_value"
        assert env_var.description == "Test environment variable"
        assert env_var.is_encrypted == False

    def test_create_env_var_invalid_data(self, clean_db, envar_crud, invalid_env_var_data):
        """Geçersiz alanlar ile environment variable oluşturma testi - geçersiz alanlar filtrelenir"""
        env_var = envar_crud.create_env_var(clean_db, **invalid_env_var_data)

        assert env_var is not None
        assert env_var.id is not None
        assert env_var.id.startswith("EV-")
        assert env_var.created_at is not None
        assert env_var.updated_at is not None
        assert env_var.name == "TEST_VAR"
        assert env_var.value == "test_value"
        assert env_var.description == "Test environment variable"
        assert env_var.is_encrypted == False
        
        # Geçersiz alanın filtrelendiğini doğrula
        assert not hasattr(env_var, "random_col")

    def test_update_env_var_valid_data(self, clean_db, envar_crud, sample_env_var_data):
        env_var = envar_crud.create_env_var(clean_db, **sample_env_var_data)

        update_payload = {
            "value": "updated_value",
            "description": "Updated description",
            "is_encrypted": True
        }

        updated_env_var = envar_crud.update_env_var(clean_db, env_var.id, **update_payload)

        assert updated_env_var.id == env_var.id
        assert updated_env_var.name == env_var.name
        assert updated_env_var.value == "updated_value"
        assert updated_env_var.description == "Updated description"
        assert updated_env_var.is_encrypted == True
        assert updated_env_var.updated_at != env_var.created_at

    def test_update_env_var_invalid_data(self, clean_db, envar_crud, sample_env_var_data):
        env_var = envar_crud.create_env_var(clean_db, **sample_env_var_data)

        invalid_update_payload = {
            "value": "updated_value",
            "random_field": "invalid_value"
        }

        updated_env_var = envar_crud.update_env_var(clean_db, env_var.id, **invalid_update_payload)

        assert updated_env_var.id == env_var.id
        assert updated_env_var.value == "updated_value"
        # Geçersiz alanın filtrelendiğini doğrula
        assert not hasattr(updated_env_var, "random_field")

    def test_update_env_var_invalid_id(self, clean_db, envar_crud, sample_env_var_data):
        """Geçersiz ID ile environment variable güncelleme testi"""
        with pytest.raises(CRUDException, match="No such record EV-INVALID"):
            envar_crud.update_env_var(clean_db, "EV-INVALID", value="updated")

    def test_delete_env_var_valid_id(self, clean_db, envar_crud, sample_env_var_data):
        env_var = envar_crud.create_env_var(clean_db, **sample_env_var_data)
        
        deleted_env_var = envar_crud.delete_env_var(clean_db, env_var.id)
        
        assert deleted_env_var.id == env_var.id
        assert deleted_env_var.name == env_var.name
        
        # Environment variable"ın gerçekten silindiğini doğrula
        with pytest.raises(CRUDException, match=f"No such record {env_var.id}"):
            envar_crud.find_by_id(clean_db, env_var.id)

    def test_delete_env_var_invalid_id(self, clean_db, envar_crud):
        """Geçersiz ID ile environment variable silme testi"""
        with pytest.raises(CRUDException, match="No such record EV-INVALID"):
            envar_crud.delete_env_var(clean_db, "EV-INVALID")

    def test_find_by_id_valid(self, clean_db, envar_crud, sample_env_var_data):
        env_var = envar_crud.create_env_var(clean_db, **sample_env_var_data)
        
        found_env_var = envar_crud.find_by_id(clean_db, env_var.id)
        
        assert found_env_var is not None
        assert found_env_var.id == env_var.id
        assert found_env_var.name == env_var.name
        assert found_env_var.value == env_var.value

    def test_find_by_id_invalid(self, clean_db, envar_crud):
        """Geçersiz ID ile environment variable bulma testi"""
        with pytest.raises(CRUDException, match="No such record EV-INVALID"):
            envar_crud.find_by_id(clean_db, "EV-INVALID")
