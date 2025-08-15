import pytest

from miniflow.database.models import Edge, ConditionType
from miniflow.exceptions import CRUDException


@pytest.fixture
def sample_edge_data():
    """Test için sample edge data"""
    return {
        "workflow_id": "WF-TEST-001",
        "from_node_id": "ND-TEST-001",
        "to_node_id": "ND-TEST-002",
        "condition_type": ConditionType.SUCCESS
    }


@pytest.fixture
def invalid_edge_data():
    """Test için invalid edge data"""
    return {
        "workflow_id": "WF-TEST-001",
        "from_node_id": "ND-TEST-001",
        "to_node_id": "ND-TEST-002",
        "condition_type": ConditionType.SUCCESS,
        "random_col": 4
    }


@pytest.mark.unittest
class TestEdgeCrudBasic:
    """Temel CRUD işlemleri testleri"""
    
    def test_edge_crud_initialization(self, edge_crud):
        assert edge_crud.model == Edge
        assert edge_crud.model_name == "Edge"

    def test_create_edge_valid_data(self, clean_db, edge_crud, sample_edge_data):
        edge = edge_crud.create_edge(clean_db, **sample_edge_data)

        assert edge is not None
        assert edge.id is not None
        assert edge.id.startswith("ED-")
        assert edge.created_at is not None
        assert edge.updated_at is not None
        assert edge.workflow_id == "WF-TEST-001"
        assert edge.from_node_id == "ND-TEST-001"
        assert edge.to_node_id == "ND-TEST-002"
        assert edge.condition_type == ConditionType.SUCCESS

    def test_create_edge_invalid_data(self, clean_db, edge_crud, invalid_edge_data):
        """Geçersiz alanlar ile edge oluşturma testi - geçersiz alanlar filtrelenir"""
        edge = edge_crud.create_edge(clean_db, **invalid_edge_data)

        assert edge is not None
        assert edge.id is not None
        assert edge.id.startswith("ED-")
        assert edge.created_at is not None
        assert edge.updated_at is not None
        assert edge.workflow_id == "WF-TEST-001"
        assert edge.from_node_id == "ND-TEST-001"
        assert edge.to_node_id == "ND-TEST-002"
        assert edge.condition_type == ConditionType.SUCCESS
        
        # Geçersiz alanın filtrelendiğini doğrula
        assert not hasattr(edge, "random_col")

    def test_update_edge_valid_data(self, clean_db, edge_crud, sample_edge_data):
        edge = edge_crud.create_edge(clean_db, **sample_edge_data)

        update_payload = {
            "condition_type": ConditionType.FAILURE
        }

        updated_edge = edge_crud.update_edge(clean_db, edge.id, **update_payload)

        assert updated_edge.id == edge.id
        assert updated_edge.workflow_id == edge.workflow_id
        assert updated_edge.from_node_id == edge.from_node_id
        assert updated_edge.to_node_id == edge.to_node_id
        assert updated_edge.condition_type == ConditionType.FAILURE
        assert updated_edge.updated_at != edge.created_at

    def test_update_edge_invalid_data(self, clean_db, edge_crud, sample_edge_data):
        edge = edge_crud.create_edge(clean_db, **sample_edge_data)

        invalid_update_payload = {
            "condition_type": ConditionType.FAILURE,
            "random_field": "invalid_value"
        }

        updated_edge = edge_crud.update_edge(clean_db, edge.id, **invalid_update_payload)

        assert updated_edge.id == edge.id
        assert updated_edge.condition_type == ConditionType.FAILURE
        # Geçersiz alanın filtrelendiğini doğrula
        assert not hasattr(updated_edge, "random_field")

    def test_update_edge_invalid_id(self, clean_db, edge_crud, sample_edge_data):
        """Geçersiz ID ile edge güncelleme testi"""
        with pytest.raises(CRUDException, match="No such record ED-INVALID"):
            edge_crud.update_edge(clean_db, "ED-INVALID", condition_type=ConditionType.FAILURE)

    def test_delete_edge_valid_id(self, clean_db, edge_crud, sample_edge_data):
        edge = edge_crud.create_edge(clean_db, **sample_edge_data)
        
        deleted_edge = edge_crud.delete_edge(clean_db, edge.id)
        
        assert deleted_edge.id == edge.id
        assert deleted_edge.workflow_id == edge.workflow_id
        
        # Edge"in gerçekten silindiğini doğrula
        with pytest.raises(CRUDException, match=f"No such record {edge.id}"):
            edge_crud.find_by_id(clean_db, edge.id)

    def test_delete_edge_invalid_id(self, clean_db, edge_crud):
        """Geçersiz ID ile edge silme testi"""
        with pytest.raises(CRUDException, match="No such record ED-INVALID"):
            edge_crud.delete_edge(clean_db, "ED-INVALID")

    def test_find_by_id_valid(self, clean_db, edge_crud, sample_edge_data):
        edge = edge_crud.create_edge(clean_db, **sample_edge_data)
        
        found_edge = edge_crud.find_by_id(clean_db, edge.id)
        
        assert found_edge is not None
        assert found_edge.id == edge.id
        assert found_edge.workflow_id == edge.workflow_id
        assert found_edge.from_node_id == edge.from_node_id

    def test_find_by_id_invalid(self, clean_db, edge_crud):
        """Geçersiz ID ile edge bulma testi"""
        with pytest.raises(CRUDException, match="No such record ED-INVALID"):
            edge_crud.find_by_id(clean_db, "ED-INVALID")
