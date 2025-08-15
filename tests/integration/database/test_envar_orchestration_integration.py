# tests/integration/database/test_envar_orchestration_integration.py
import pytest
from sqlalchemy.orm import Session

from miniflow.database.orchestration.envar_orchestration import EnvarOrchestrator
from miniflow.database.models import EnvironmentVariable
from miniflow.exceptions import ValidationError, BusinessLogicError


@pytest.fixture
def envar_orchestrator():
    return EnvarOrchestrator()


@pytest.fixture
def sample_envar_data():
    """Sample environment variable data for testing"""
    return {
        'name': 'TEST_API_KEY',
        'value': 'secret_api_key_123',
        'description': 'Test API key for integration testing',
        'is_encrypted': False
    }


@pytest.fixture
def sample_encrypted_envar_data():
    """Sample encrypted environment variable data for testing"""
    return {
        'name': 'ENCRYPTED_PASSWORD',
        'value': 'super_secret_password',
        'description': 'Encrypted password for testing',
        'is_encrypted': True
    }


@pytest.mark.integration
class TestEnvarOrchestrationCreate:
    def test_create_envar_with_valid_data(self, clean_db, envar_orchestrator, sample_envar_data):
        # Create environment variable
        result = envar_orchestrator.create(clean_db, sample_envar_data)
        
        # Verify response structure
        assert result is not None
        assert 'id' in result
        assert result['name'] == sample_envar_data['name']
        assert result['value'] == sample_envar_data['value']
        assert result['description'] == sample_envar_data['description']
        assert result['is_encrypted'] == sample_envar_data['is_encrypted']
        
        # Verify in database
        db_envar = clean_db.get(EnvironmentVariable, result['id'])
        assert db_envar is not None
        assert db_envar.name == sample_envar_data['name']
        assert db_envar.value == sample_envar_data['value']
        assert db_envar.is_encrypted == sample_envar_data['is_encrypted']

    def test_create_encrypted_envar(self, clean_db, envar_orchestrator, sample_encrypted_envar_data):
        # Create encrypted environment variable
        result = envar_orchestrator.create(clean_db, sample_encrypted_envar_data)
        
        # Verify response structure
        assert result is not None
        assert result['name'] == sample_encrypted_envar_data['name']
        assert result['is_encrypted'] == True
        
        # Verify value is encrypted (not the original)
        assert result['value'] != sample_encrypted_envar_data['value']
        
        # Verify in database
        db_envar = clean_db.get(EnvironmentVariable, result['id'])
        assert db_envar is not None
        assert db_envar.value != sample_encrypted_envar_data['value']  # Should be encrypted
        assert db_envar.is_encrypted == True
        
        # Verify we can decrypt it back
        orchestrator = envar_orchestrator
        decrypted = orchestrator._decrypt_value(db_envar.value)
        assert decrypted == sample_encrypted_envar_data['value']

    def test_create_envar_with_missing_name(self, clean_db, envar_orchestrator, sample_envar_data):
        # Remove name
        del sample_envar_data['name']
        
        # Attempt to create environment variable
        with pytest.raises(ValidationError) as exc_info:
            envar_orchestrator.create(clean_db, sample_envar_data)
        
        assert "Environment variable name is required" in str(exc_info.value)

    def test_create_envar_with_empty_name(self, clean_db, envar_orchestrator, sample_envar_data):
        # Set empty name
        sample_envar_data['name'] = ''
        
        # Attempt to create environment variable
        with pytest.raises(ValidationError) as exc_info:
            envar_orchestrator.create(clean_db, sample_envar_data)
        
        assert "Environment variable name is required" in str(exc_info.value)

    def test_create_envar_with_whitespace_name(self, clean_db, envar_orchestrator, sample_envar_data):
        # Set whitespace name
        sample_envar_data['name'] = '   '
        
        # Attempt to create environment variable
        with pytest.raises(ValidationError) as exc_info:
            envar_orchestrator.create(clean_db, sample_envar_data)
        
        assert "Environment variable name is required" in str(exc_info.value)

    def test_create_envar_with_invalid_name_characters(self, clean_db, envar_orchestrator, sample_envar_data):
        # Set invalid name with special characters
        sample_envar_data['name'] = 'INVALID@NAME!'
        
        # Attempt to create environment variable
        with pytest.raises(ValidationError) as exc_info:
            envar_orchestrator.create(clean_db, sample_envar_data)
        
        assert "must contain only alphanumeric characters, hyphens, and underscores" in str(exc_info.value)

    def test_create_envar_with_valid_name_characters(self, clean_db, envar_orchestrator, sample_envar_data):
        # Test valid characters: alphanumeric, hyphens, underscores
        valid_names = ['API_KEY', 'api-key', 'API123', 'test_var_123', 'MY-ENV-VAR']
        
        for i, name in enumerate(valid_names):
            envar_data = sample_envar_data.copy()
            envar_data['name'] = name
            
            # Should not raise any exception
            result = envar_orchestrator.create(clean_db, envar_data)
            assert result is not None
            assert result['name'] == name

    def test_create_duplicate_envar_name(self, clean_db, envar_orchestrator, sample_envar_data):
        # Create first environment variable
        envar1 = envar_orchestrator.create(clean_db, sample_envar_data)
        assert envar1 is not None
        
        # Attempt to create duplicate
        with pytest.raises(ValidationError) as exc_info:
            envar_orchestrator.create(clean_db, sample_envar_data)
        
        assert f"Environment variable with name '{sample_envar_data['name']}' already exists" in str(exc_info.value)

    def test_create_envar_with_empty_value(self, clean_db, envar_orchestrator, sample_envar_data):
        # Set empty value
        sample_envar_data['value'] = ''
        
        # Should succeed (empty values are valid)
        result = envar_orchestrator.create(clean_db, sample_envar_data)
        
        assert result is not None
        assert result['value'] == ''

    def test_create_envar_without_value(self, clean_db, envar_orchestrator, sample_envar_data):
        # Remove value field
        del sample_envar_data['value']
        
        # Should fail with database constraint error (value is NOT NULL)
        with pytest.raises(Exception):  # SQLAlchemy wraps it in IntegrityError
            envar_orchestrator.create(clean_db, sample_envar_data)

    def test_create_envar_with_minimal_data(self, clean_db, envar_orchestrator):
        # Create with only required fields
        minimal_data = {
            'name': 'MINIMAL_VAR',
            'value': 'minimal_value'
        }
        
        result = envar_orchestrator.create(clean_db, minimal_data)
        
        assert result is not None
        assert result['name'] == 'MINIMAL_VAR'
        assert result['value'] == 'minimal_value'
        assert result['is_encrypted'] == False  # Default value


@pytest.mark.integration
class TestEnvarOrchestrationUpdate:
    def test_update_envar_with_valid_data(self, clean_db, envar_orchestrator, sample_envar_data):
        # Create environment variable
        envar = envar_orchestrator.create(clean_db, sample_envar_data)
        
        # Update environment variable
        update_data = {
            'value': 'updated_secret_key',
            'description': 'Updated description'
        }
        result = envar_orchestrator.update(clean_db, envar['id'], update_data)
        
        # Verify response
        assert result is not None
        assert result['id'] == envar['id']
        assert result['value'] == 'updated_secret_key'
        assert result['description'] == 'Updated description'
        assert result['name'] == sample_envar_data['name']  # Should remain unchanged
        
        # Verify in database
        db_envar = clean_db.get(EnvironmentVariable, envar['id'])
        assert db_envar.value == 'updated_secret_key'
        assert db_envar.description == 'Updated description'

    def test_update_envar_with_invalid_id(self, clean_db, envar_orchestrator):
        # Attempt to update non-existent environment variable
        update_data = {'value': 'new_value'}
        
        with pytest.raises(BusinessLogicError) as exc_info:
            envar_orchestrator.update(clean_db, 'INVALID-ENVAR-ID', update_data)
        
        assert "Environment variable not found" in str(exc_info.value)

    def test_update_envar_name_with_valid_name(self, clean_db, envar_orchestrator, sample_envar_data):
        # Create environment variable
        envar = envar_orchestrator.create(clean_db, sample_envar_data)
        
        # Update name
        update_data = {'name': 'UPDATED_API_KEY'}
        result = envar_orchestrator.update(clean_db, envar['id'], update_data)
        
        # Verify response
        assert result is not None
        assert result['name'] == 'UPDATED_API_KEY'
        
        # Verify in database
        db_envar = clean_db.get(EnvironmentVariable, envar['id'])
        assert db_envar.name == 'UPDATED_API_KEY'

    def test_update_envar_name_with_empty_name(self, clean_db, envar_orchestrator, sample_envar_data):
        # Create environment variable
        envar = envar_orchestrator.create(clean_db, sample_envar_data)
        
        # Attempt to update with empty name
        update_data = {'name': ''}
        
        with pytest.raises(ValidationError) as exc_info:
            envar_orchestrator.update(clean_db, envar['id'], update_data)
        
        assert "Environment variable name is required" in str(exc_info.value)

    def test_update_envar_name_with_invalid_characters(self, clean_db, envar_orchestrator, sample_envar_data):
        # Create environment variable
        envar = envar_orchestrator.create(clean_db, sample_envar_data)
        
        # Attempt to update with invalid name
        update_data = {'name': 'INVALID@NAME!'}
        
        with pytest.raises(ValidationError) as exc_info:
            envar_orchestrator.update(clean_db, envar['id'], update_data)
        
        assert "must contain only alphanumeric characters, hyphens, and underscores" in str(exc_info.value)

    def test_update_envar_name_to_existing_name(self, clean_db, envar_orchestrator, sample_envar_data):
        # Create first environment variable
        envar1 = envar_orchestrator.create(clean_db, sample_envar_data)
        
        # Create second environment variable
        envar_data2 = sample_envar_data.copy()
        envar_data2['name'] = 'SECOND_API_KEY'
        envar2 = envar_orchestrator.create(clean_db, envar_data2)
        
        # Attempt to update second env var name to first's name
        update_data = {'name': sample_envar_data['name']}
        
        with pytest.raises(ValidationError) as exc_info:
            envar_orchestrator.update(clean_db, envar2['id'], update_data)
        
        assert f"Environment variable with name '{sample_envar_data['name']}' already exists" in str(exc_info.value)

    def test_update_envar_to_encrypted(self, clean_db, envar_orchestrator, sample_envar_data):
        # Create unencrypted environment variable
        envar = envar_orchestrator.create(clean_db, sample_envar_data)
        original_value = sample_envar_data['value']
        
        # Update to encrypted
        update_data = {
            'is_encrypted': True,
            'value': 'new_secret_value'
        }
        result = envar_orchestrator.update(clean_db, envar['id'], update_data)
        
        # Verify response
        assert result is not None
        assert result['is_encrypted'] == True
        assert result['value'] != 'new_secret_value'  # Should be encrypted
        
        # Verify in database
        db_envar = clean_db.get(EnvironmentVariable, envar['id'])
        assert db_envar.is_encrypted == True
        assert db_envar.value != 'new_secret_value'  # Should be encrypted
        
        # Verify we can decrypt it
        orchestrator = envar_orchestrator
        decrypted = orchestrator._decrypt_value(db_envar.value)
        assert decrypted == 'new_secret_value'

    def test_update_envar_from_encrypted_to_unencrypted(self, clean_db, envar_orchestrator, sample_encrypted_envar_data):
        # Create encrypted environment variable
        envar = envar_orchestrator.create(clean_db, sample_encrypted_envar_data)
        
        # Update to unencrypted
        update_data = {
            'is_encrypted': False,
            'value': 'plain_text_value'
        }
        result = envar_orchestrator.update(clean_db, envar['id'], update_data)
        
        # Verify response
        assert result is not None
        assert result['is_encrypted'] == False
        # Note: Value will still be encrypted in this case due to the logic
        
        # Verify in database
        db_envar = clean_db.get(EnvironmentVariable, envar['id'])
        assert db_envar.is_encrypted == False


@pytest.mark.integration
class TestEnvarOrchestrationDelete:
    def test_delete_envar_with_valid_id(self, clean_db, envar_orchestrator, sample_envar_data):
        # Create environment variable
        envar = envar_orchestrator.create(clean_db, sample_envar_data)
        
        # Delete environment variable
        result = envar_orchestrator.delete(clean_db, envar['id'])
        
        # Verify response
        assert result is not None
        assert result['id'] == envar['id']
        
        # Verify deletion in database
        db_envar = clean_db.get(EnvironmentVariable, envar['id'])
        assert db_envar is None

    def test_delete_envar_with_invalid_id(self, clean_db, envar_orchestrator):
        # Attempt to delete non-existent environment variable
        with pytest.raises(BusinessLogicError) as exc_info:
            envar_orchestrator.delete(clean_db, 'INVALID-ENVAR-ID')
        
        assert "Environment variable not found" in str(exc_info.value)


@pytest.mark.integration
class TestEnvarOrchestrationGet:
    def test_get_envar_with_valid_id(self, clean_db, envar_orchestrator, sample_envar_data):
        # Create environment variable
        envar = envar_orchestrator.create(clean_db, sample_envar_data)
        
        # Get environment variable
        result = envar_orchestrator.get(clean_db, envar['id'])
        
        # Verify response
        assert result is not None
        assert result['id'] == envar['id']
        assert result['name'] == sample_envar_data['name']
        assert result['value'] == sample_envar_data['value']
        assert result['description'] == sample_envar_data['description']
        assert result['is_encrypted'] == sample_envar_data['is_encrypted']

    def test_get_envar_with_invalid_id(self, clean_db, envar_orchestrator):
        # Attempt to get non-existent environment variable
        with pytest.raises(BusinessLogicError) as exc_info:
            envar_orchestrator.get(clean_db, 'INVALID-ENVAR-ID')
        
        assert "Environment variable not found" in str(exc_info.value)

    def test_get_encrypted_envar_without_decryption(self, clean_db, envar_orchestrator, sample_encrypted_envar_data):
        # Create encrypted environment variable
        envar = envar_orchestrator.create(clean_db, sample_encrypted_envar_data)
        
        # Get environment variable without decryption
        result = envar_orchestrator.get(clean_db, envar['id'], include_decrypted=False)
        
        # Verify response
        assert result is not None
        assert result['is_encrypted'] == True
        assert result['value'] != sample_encrypted_envar_data['value']  # Should be encrypted
        assert 'decrypted_value' not in result

    def test_get_encrypted_envar_with_decryption(self, clean_db, envar_orchestrator, sample_encrypted_envar_data):
        # Create encrypted environment variable
        envar = envar_orchestrator.create(clean_db, sample_encrypted_envar_data)
        
        # Get environment variable with decryption
        result = envar_orchestrator.get(clean_db, envar['id'], include_decrypted=True)
        
        # Verify response
        assert result is not None
        assert result['is_encrypted'] == True
        assert result['value'] != sample_encrypted_envar_data['value']  # Should still be encrypted
        assert 'decrypted_value' in result
        assert result['decrypted_value'] == sample_encrypted_envar_data['value']  # Should be decrypted

    def test_get_unencrypted_envar_with_decryption_flag(self, clean_db, envar_orchestrator, sample_envar_data):
        # Create unencrypted environment variable
        envar = envar_orchestrator.create(clean_db, sample_envar_data)
        
        # Get environment variable with decryption flag (should have no effect)
        result = envar_orchestrator.get(clean_db, envar['id'], include_decrypted=True)
        
        # Verify response
        assert result is not None
        assert result['is_encrypted'] == False
        assert result['value'] == sample_envar_data['value']
        assert 'decrypted_value' not in result  # Should not be present for unencrypted


@pytest.mark.integration
class TestEnvarOrchestrationSearch:
    def test_search_envar_with_name_criteria(self, clean_db, envar_orchestrator, sample_envar_data):
        # Create environment variable
        envar = envar_orchestrator.create(clean_db, sample_envar_data)
        
        # Search by name
        search_criteria = {'name': sample_envar_data['name']}
        result = envar_orchestrator.search(clean_db, search_criteria)
        
        # Verify response
        assert result is not None
        assert 'data' in result
        assert 'total_count' in result
        assert result['total_count'] >= 1
        assert len(result['data']) >= 1
        
        # Verify environment variable is in results
        envar_found = any(e['id'] == envar['id'] for e in result['data'])
        assert envar_found

    def test_search_envar_with_encryption_criteria(self, clean_db, envar_orchestrator, sample_envar_data, sample_encrypted_envar_data):
        # Create unencrypted environment variable
        envar1 = envar_orchestrator.create(clean_db, sample_envar_data)
        
        # Create encrypted environment variable
        envar2 = envar_orchestrator.create(clean_db, sample_encrypted_envar_data)
        
        # Search for encrypted variables
        search_criteria = {'is_encrypted': True}
        result = envar_orchestrator.search(clean_db, search_criteria)
        
        # Verify response
        assert result is not None
        assert result['total_count'] >= 1
        
        # Verify all results are encrypted
        for envar_data in result['data']:
            assert envar_data['is_encrypted'] == True

        # Search for unencrypted variables
        search_criteria = {'is_encrypted': False}
        result = envar_orchestrator.search(clean_db, search_criteria)
        
        # Verify response
        assert result is not None
        assert result['total_count'] >= 1
        
        # Verify all results are unencrypted
        for envar_data in result['data']:
            assert envar_data['is_encrypted'] == False

    def test_search_envar_with_pagination(self, clean_db, envar_orchestrator, sample_envar_data):
        # Create multiple environment variables
        envars = []
        for i in range(5):
            envar_data = sample_envar_data.copy()
            envar_data['name'] = f'TEST_VAR_{i}'
            envar = envar_orchestrator.create(clean_db, envar_data)
            envars.append(envar)
        
        # Search with pagination
        search_criteria = {}  # Get all
        result = envar_orchestrator.search(clean_db, search_criteria, skip=0, limit=3)
        
        # Verify pagination
        assert result is not None
        assert len(result['data']) <= 3
        assert result['total_count'] >= 5
        assert result['skip'] == 0
        assert result['limit'] == 3
        assert result['has_more'] == True

    def test_search_envar_with_invalid_criteria(self, clean_db, envar_orchestrator):
        # Search with criteria that matches nothing
        search_criteria = {'name': 'NON_EXISTENT_VAR'}
        result = envar_orchestrator.search(clean_db, search_criteria)
        
        # Verify empty result
        assert result is not None
        assert result['total_count'] == 0
        assert len(result['data']) == 0


@pytest.mark.integration
class TestEnvarOrchestrationExtraOperations:
    def test_count_envars(self, clean_db, envar_orchestrator, sample_envar_data):
        # Get initial count
        initial_count = envar_orchestrator.count(clean_db)
        
        # Create environment variable
        envar = envar_orchestrator.create(clean_db, sample_envar_data)
        
        # Verify count increased
        new_count = envar_orchestrator.count(clean_db)
        assert new_count == initial_count + 1

    def test_exists_envar_with_valid_id(self, clean_db, envar_orchestrator, sample_envar_data):
        # Create environment variable
        envar = envar_orchestrator.create(clean_db, sample_envar_data)
        
        # Check existence
        exists = envar_orchestrator.exists(clean_db, envar['id'])
        assert exists == True

    def test_exists_envar_with_invalid_id(self, clean_db, envar_orchestrator):
        # Check non-existent environment variable
        exists = envar_orchestrator.exists(clean_db, 'INVALID-ENVAR-ID')
        assert exists == False

    def test_get_all_envars(self, clean_db, envar_orchestrator, sample_envar_data):
        # Create environment variable
        envar = envar_orchestrator.create(clean_db, sample_envar_data)
        
        # Get all environment variables
        result = envar_orchestrator.get_all(clean_db)
        
        # Verify response
        assert result is not None
        assert isinstance(result, list)
        assert len(result) >= 1
        
        # Verify our environment variable is in the list
        envar_found = any(e['id'] == envar['id'] for e in result)
        assert envar_found

    def test_get_by_encrypted_status(self, clean_db, envar_orchestrator, sample_envar_data, sample_encrypted_envar_data):
        # Create unencrypted environment variable
        unencrypted_envar = envar_orchestrator.create(clean_db, sample_envar_data)
        
        # Create encrypted environment variable
        encrypted_envar = envar_orchestrator.create(clean_db, sample_encrypted_envar_data)
        
        # Get encrypted environment variables
        encrypted_result = envar_orchestrator.get_by_encrypted_status(clean_db, True)
        
        # Verify response
        assert encrypted_result is not None
        assert isinstance(encrypted_result, list)
        assert len(encrypted_result) >= 1
        
        # Verify all results are encrypted
        for envar in encrypted_result:
            assert envar['is_encrypted'] == True
        
        # Verify our encrypted env var is in results
        encrypted_found = any(e['id'] == encrypted_envar['id'] for e in encrypted_result)
        assert encrypted_found
        
        # Get unencrypted environment variables
        unencrypted_result = envar_orchestrator.get_by_encrypted_status(clean_db, False)
        
        # Verify response
        assert unencrypted_result is not None
        assert isinstance(unencrypted_result, list)
        assert len(unencrypted_result) >= 1
        
        # Verify all results are unencrypted
        for envar in unencrypted_result:
            assert envar['is_encrypted'] == False
        
        # Verify our unencrypted env var is in results
        unencrypted_found = any(e['id'] == unencrypted_envar['id'] for e in unencrypted_result)
        assert unencrypted_found

    def test_get_encrypted_envars(self, clean_db, envar_orchestrator, sample_encrypted_envar_data):
        # Create encrypted environment variable
        encrypted_envar = envar_orchestrator.create(clean_db, sample_encrypted_envar_data)
        
        # Get encrypted environment variables
        result = envar_orchestrator.get_encrypted_envars(clean_db)
        
        # Verify response
        assert result is not None
        assert isinstance(result, list)
        assert len(result) >= 1
        
        # Verify all results are encrypted
        for envar in result:
            assert envar['is_encrypted'] == True
        
        # Verify our encrypted env var is in results
        encrypted_found = any(e['id'] == encrypted_envar['id'] for e in result)
        assert encrypted_found

    def test_get_unencrypted_envars(self, clean_db, envar_orchestrator, sample_envar_data):
        # Create unencrypted environment variable
        unencrypted_envar = envar_orchestrator.create(clean_db, sample_envar_data)
        
        # Get unencrypted environment variables
        result = envar_orchestrator.get_unencrypted_envars(clean_db)
        
        # Verify response
        assert result is not None
        assert isinstance(result, list)
        assert len(result) >= 1
        
        # Verify all results are unencrypted
        for envar in result:
            assert envar['is_encrypted'] == False
        
        # Verify our unencrypted env var is in results
        unencrypted_found = any(e['id'] == unencrypted_envar['id'] for e in result)
        assert unencrypted_found


@pytest.mark.integration
class TestEnvarOrchestrationEncryption:
    def test_encrypt_value_with_valid_string(self, envar_orchestrator):
        # Test encryption
        original_value = "test_secret_123"
        encrypted_value = envar_orchestrator._encrypt_value(original_value)
        
        # Verify encryption
        assert encrypted_value != original_value
        assert len(encrypted_value) > 0
        
        # Verify we can decrypt it back
        decrypted_value = envar_orchestrator._decrypt_value(encrypted_value)
        assert decrypted_value == original_value

    def test_encrypt_value_with_empty_string(self, envar_orchestrator):
        # Test encryption with empty string
        encrypted_value = envar_orchestrator._encrypt_value("")
        
        # Should return empty string
        assert encrypted_value == ""
        
        # Decrypt should also return empty string
        decrypted_value = envar_orchestrator._decrypt_value(encrypted_value)
        assert decrypted_value == ""

    def test_encrypt_value_with_unicode_characters(self, envar_orchestrator):
        # Test encryption with unicode characters
        original_value = "şecret_päss_123_ñoñö"
        encrypted_value = envar_orchestrator._encrypt_value(original_value)
        
        # Verify encryption
        assert encrypted_value != original_value
        assert len(encrypted_value) > 0
        
        # Verify we can decrypt it back
        decrypted_value = envar_orchestrator._decrypt_value(encrypted_value)
        assert decrypted_value == original_value

    def test_decrypt_value_with_invalid_data(self, envar_orchestrator):
        # Test decryption with invalid base64 data
        with pytest.raises(ValidationError) as exc_info:
            envar_orchestrator._decrypt_value("invalid_base64_data!")
        
        assert "Failed to decrypt environment variable value" in str(exc_info.value)

    def test_decrypt_value_with_empty_string(self, envar_orchestrator):
        # Test decryption with empty string
        decrypted_value = envar_orchestrator._decrypt_value("")
        
        # Should return empty string
        assert decrypted_value == ""
