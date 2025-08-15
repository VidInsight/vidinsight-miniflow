import pytest

from miniflow.database.models import Node
from miniflow.exceptions import CRUDException


@pytest.fixture
def sample_node_data():
    """Test için sample node data"""
    return {
        "workflow_id": "WF-TEST-001",
        "script_id": "SC-TEST-001",
        "name": "test_node",
        "description": "Test node description",
        "params": {
            "timeout": 300,
            "retries": 3,
            "priority": "high"
        },
        "max_retries": 3,
        "timeout_seconds": 300
    }


@pytest.fixture
def invalid_node_data():
    """Test için invalid node data"""
    return {
        "workflow_id": "WF-TEST-001",
        "script_id": "SC-TEST-001",
        "name": "test_node",
        "description": "Test node description",
        "params": {
            "timeout": 300,
            "retries": 3,
            "priority": "high"
        },
        "max_retries": 3,
        "timeout_seconds": 300,
        "random_col": 4
    }


@pytest.fixture
def multiple_node_data():
    """Multiple node data for bulk operations"""
    return [
        {
            "workflow_id": "WF-TEST-001",
            "script_id": "SC-TEST-001",
            "name": "node_1",
            "description": "First node",
            "params": {"param1": "value1"},
            "max_retries": 3,
            "timeout_seconds": 300
        },
        {
            "workflow_id": "WF-TEST-001",
            "script_id": "SC-TEST-002",
            "name": "node_2",
            "description": "Second node",
            "params": {"param2": "value2"},
            "max_retries": 5,
            "timeout_seconds": 600
        },
        {
            "workflow_id": "WF-TEST-002",
            "script_id": "SC-TEST-003",
            "name": "node_3",
            "description": "Third node",
            "params": {"param3": "value3"},
            "max_retries": 2,
            "timeout_seconds": 150
        }
    ]


@pytest.mark.unittest
class TestNodeCrudBasic:
    """Temel CRUD işlemleri testleri"""
    
    def test_node_crud_initialization(self, node_crud):
        assert node_crud.model == Node
        assert node_crud.model_name == "Node"

    def test_create_node_valid_data(self, clean_db, node_crud, sample_node_data):
        node = node_crud.create_node(clean_db, **sample_node_data)

        assert node is not None
        assert node.id is not None
        assert node.id.startswith("ND-")
        assert node.created_at is not None
        assert node.updated_at is not None
        assert node.workflow_id == "WF-TEST-001"
        assert node.script_id == "SC-TEST-001"
        assert node.name == "test_node"
        assert node.description == "Test node description"
        assert node.params == {
            "timeout": 300,
            "retries": 3,
            "priority": "high"
        }
        assert node.max_retries == 3
        assert node.timeout_seconds == 300

    def test_create_node_invalid_data(self, clean_db, node_crud, invalid_node_data):
        """Geçersiz alanlar ile node oluşturma testi - geçersiz alanlar filtrelenir"""
        node = node_crud.create_node(clean_db, **invalid_node_data)

        assert node is not None
        assert node.id is not None
        assert node.id.startswith("ND-")
        assert node.created_at is not None
        assert node.updated_at is not None
        assert node.workflow_id == "WF-TEST-001"
        assert node.script_id == "SC-TEST-001"
        assert node.name == "test_node"
        assert node.description == "Test node description"
        assert node.params == {
            "timeout": 300,
            "retries": 3,
            "priority": "high"
        }
        assert node.max_retries == 3
        assert node.timeout_seconds == 300
        
        # Geçersiz alanın filtrelendiğini doğrula
        assert not hasattr(node, 'random_col')

    def test_update_node_valid_data(self, clean_db, node_crud, sample_node_data):
        node = node_crud.create_node(clean_db, **sample_node_data)

        update_payload = {
            "description": "Updated description",
            "params": {"new_param": "new_value"},
            "max_retries": 5,
            "timeout_seconds": 600
        }

        updated_node = node_crud.update_node(clean_db, node.id, **update_payload)

        assert updated_node.id == node.id
        assert updated_node.name == node.name
        assert updated_node.description == "Updated description"
        assert updated_node.params == {"new_param": "new_value"}
        assert updated_node.max_retries == 5
        assert updated_node.timeout_seconds == 600
        assert updated_node.updated_at != node.created_at

    def test_update_node_invalid_data(self, clean_db, node_crud, sample_node_data):
        node = node_crud.create_node(clean_db, **sample_node_data)

        invalid_update_payload = {
            "description": "Updated description",
            "random_field": "invalid_value"
        }

        updated_node = node_crud.update_node(clean_db, node.id, **invalid_update_payload)

        assert updated_node.id == node.id
        assert updated_node.description == "Updated description"
        # Geçersiz alanın filtrelendiğini doğrula
        assert not hasattr(updated_node, 'random_field')

    def test_update_node_invalid_id(self, clean_db, node_crud, sample_node_data):
        """Geçersiz ID ile node güncelleme testi"""
        with pytest.raises(CRUDException, match="No such record ND-INVALID"):
            node_crud.update_node(clean_db, "ND-INVALID", description="Updated")

    def test_delete_node_valid_id(self, clean_db, node_crud, sample_node_data):
        node = node_crud.create_node(clean_db, **sample_node_data)
        
        deleted_node = node_crud.delete_node(clean_db, node.id)
        
        assert deleted_node.id == node.id
        assert deleted_node.name == node.name
        
        # Node'un gerçekten silindiğini doğrula
        with pytest.raises(CRUDException, match=f"No such record {node.id}"):
            node_crud.find_by_id(clean_db, node.id)

    def test_delete_node_invalid_id(self, clean_db, node_crud):
        """Geçersiz ID ile node silme testi"""
        with pytest.raises(CRUDException, match="No such record ND-INVALID"):
            node_crud.delete_node(clean_db, "ND-INVALID")

    def test_find_by_id_valid(self, clean_db, node_crud, sample_node_data):
        node = node_crud.create_node(clean_db, **sample_node_data)
        
        found_node = node_crud.find_by_id(clean_db, node.id)
        
        assert found_node is not None
        assert found_node.id == node.id
        assert found_node.name == node.name
        assert found_node.description == node.description

    def test_find_by_id_invalid(self, clean_db, node_crud):
        """Geçersiz ID ile node bulma testi"""
        with pytest.raises(CRUDException, match="No such record ND-INVALID"):
            node_crud.find_by_id(clean_db, "ND-INVALID")


@pytest.mark.unittest
class TestNodeCrudBusinessLogic:
    """İş mantığı testleri"""
    def test_node_count_filtered_by_valid_workflow(self, clean_db, node_crud, multiple_node_data):
        for node_data in multiple_node_data:
            node_crud.create_node(clean_db, **node_data)

        count = node_crud.count_filtered(clean_db, {"workflow_id": "WF-TEST-001"})
        assert count == 2

        count = node_crud.count_filtered(clean_db, {"workflow_id": "WF-TEST-002"})
        assert count == 1

    def test_node_count_filtered_by_invalid_workflow(self, clean_db, node_crud):
        count = node_crud.count_filtered(clean_db, {"workflow_id": "WF-TEST-001"})
        assert count == 0

    def test_get_by_workflow(self, clean_db, node_crud, multiple_node_data):
        """Workflow'a göre node getirme testi"""
        for node_data in multiple_node_data:
            node_crud.create_node(clean_db, **node_data)

        # WF-TEST-001 workflow'undaki node'lar
        wf001_nodes = node_crud.get_by_workflow(clean_db, "WF-TEST-001")
        assert len(wf001_nodes) == 2
        assert all(node.workflow_id == "WF-TEST-001" for node in wf001_nodes)

        # WF-TEST-002 workflow'undaki node'lar
        wf002_nodes = node_crud.get_by_workflow(clean_db, "WF-TEST-002")
        assert len(wf002_nodes) == 1
        assert wf002_nodes[0].workflow_id == "WF-TEST-002"

    def test_get_by_script(self, clean_db, node_crud, multiple_node_data):
        """Script'e göre node getirme testi"""
        for node_data in multiple_node_data:
            node_crud.create_node(clean_db, **node_data)

        # SC-TEST-001 script'indeki node'lar
        sc001_nodes = node_crud.get_by_script(clean_db, "SC-TEST-001")
        assert len(sc001_nodes) == 1
        assert sc001_nodes[0].script_id == "SC-TEST-001"

    def test_node_name_exists_in_workflow(self, clean_db, node_crud, multiple_node_data):
        """Node ismi workflow'da var mı kontrolü testi"""
        # Henüz hiç node yok
        exists = node_crud.node_name_exists_in_workflow(clean_db, "node_1", "WF-TEST-001")
        assert exists is False

        # Node'ları oluştur
        for node_data in multiple_node_data:
            node_crud.create_node(clean_db, **node_data)

        # Var olan node isimleri için True dönmeli
        exists = node_crud.node_name_exists_in_workflow(clean_db, "node_1", "WF-TEST-001")
        assert exists is True

        exists = node_crud.node_name_exists_in_workflow(clean_db, "node_2", "WF-TEST-001")
        assert exists is True

        exists = node_crud.node_name_exists_in_workflow(clean_db, "node_3", "WF-TEST-002")
        assert exists is True

        # Olmayan node isimleri için False dönmeli
        exists = node_crud.node_name_exists_in_workflow(clean_db, "nonexistent", "WF-TEST-001")
        assert exists is False

        # Yanlış workflow'da arama yapılınca False dönmeli
        exists = node_crud.node_name_exists_in_workflow(clean_db, "node_1", "WF-TEST-002")
        assert exists is False

        # Var olan isim ama yanlış workflow
        exists = node_crud.node_name_exists_in_workflow(clean_db, "node_3", "WF-TEST-001")
        assert exists is False

    def test_node_name_exists_in_workflow_empty_database(self, clean_db, node_crud):
        """Boş veritabanında node existence kontrolü"""
        exists = node_crud.node_name_exists_in_workflow(clean_db, "any_name", "ANY-WORKFLOW")
        assert exists is False