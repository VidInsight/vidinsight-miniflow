import pytest
import uuid
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError

from miniflow.database_manager.models import (
    WorkflowStatus, ExecutionStatus, ExecutionOutputStatus,
    ConditionType, ScriptType, ScriptTestStatus, AuditAction, ArchiveReason,
    BaseModel, Workflow, Node, Edge, Script, Execution,
    ExecutionInput, ExecutionOutput, ArchivedExecution, AuditLog
)


class TestEnums:
    """Enum testleri"""

    def test_workflow_status_values(self, enum_test_data):
        """WorkflowStatus enum değerlerini test eder"""
        expected_values = enum_test_data["workflow_statuses"]
        actual_values = [status.value for status in WorkflowStatus]
        assert actual_values == expected_values

    def test_workflow_status_count(self):
        """WorkflowStatus enum sayısını test eder"""
        assert len(WorkflowStatus) == 4

    def test_execution_status_values(self, enum_test_data):
        """ExecutionStatus enum değerlerini test eder"""
        expected_values = enum_test_data["execution_statuses"]
        actual_values = [status.value for status in ExecutionStatus]
        assert actual_values == expected_values

    def test_execution_status_count(self):
        """ExecutionStatus enum sayısını test eder"""
        assert len(ExecutionStatus) == 5

    def test_execution_output_status_values(self, enum_test_data):
        """ExecutionOutputStatus enum değerlerini test eder"""
        expected_values = enum_test_data["execution_output_statuses"]
        actual_values = [status.value for status in ExecutionOutputStatus]
        assert actual_values == expected_values

    def test_execution_output_status_count(self):
        """ExecutionOutputStatus enum sayısını test eder"""
        assert len(ExecutionOutputStatus) == 4

    def test_condition_type_values(self, enum_test_data):
        """ConditionType enum değerlerini test eder"""
        expected_values = enum_test_data["condition_types"]
        actual_values = [condition.value for condition in ConditionType]
        assert actual_values == expected_values

    def test_condition_type_count(self):
        """ConditionType enum sayısını test eder"""
        assert len(ConditionType) == 4

    def test_script_type_values(self, enum_test_data):
        """ScriptType enum değerlerini test eder"""
        expected_values = enum_test_data["script_types"]
        actual_values = [script_type.value for script_type in ScriptType]
        assert actual_values == expected_values

    def test_script_type_count(self):
        """ScriptType enum sayısını test eder"""
        assert len(ScriptType) == 1

    def test_test_status_values(self, enum_test_data):
        """ScriptTestStatus enum değerlerini test eder"""
        expected_values = enum_test_data["test_statuses"]
        actual_values = [test_status.value for test_status in ScriptTestStatus]
        assert actual_values == expected_values

    def test_test_status_count(self):
        """ScriptTestStatus enum sayısını test eder"""
        assert len(ScriptTestStatus) == 4

    def test_audit_action_values(self, enum_test_data):
        """AuditAction enum değerlerini test eder"""
        expected_values = enum_test_data["audit_actions"]
        actual_values = [action.value for action in AuditAction]
        assert actual_values == expected_values

    def test_audit_action_count(self):
        """AuditAction enum sayısını test eder"""
        assert len(AuditAction) == 5

    def test_archive_reason_values(self, enum_test_data):
        """ArchiveReason enum değerlerini test eder"""
        expected_values = enum_test_data["archive_reasons"]
        actual_values = [reason.value for reason in ArchiveReason]
        assert actual_values == expected_values

    def test_archive_reason_count(self):
        """ArchiveReason enum sayısını test eder"""
        assert len(ArchiveReason) == 4


class TestBaseModel:
    """BaseModel testleri"""

    def test_id_generation(self):
        """ID generation fonksiyonunu test eder"""
        # Test with Workflow (prefix: WF)
        id1 = Workflow._generate_id()
        id2 = Workflow._generate_id()
        
        # IDs should be different
        assert id1 != id2
        
        # ID format should be correct
        assert len(id1) == 12
        assert id1.startswith("WF")
        assert len(id2) == 12
        assert id2.startswith("WF")

    def test_id_generation_with_different_prefixes(self):
        """Farklı prefix'lerle ID generation test eder"""
        workflow_id = Workflow._generate_id()
        node_id = Node._generate_id()
        script_id = Script._generate_id()
        
        assert workflow_id.startswith("WF")
        assert node_id.startswith("ND")
        assert script_id.startswith("SC")

    def test_timestamps_creation(self, test_database_session):
        """Timestamp'lerin otomatik oluşturulmasını test eder"""
        unique_name = f"Test Workflow Timestamps {uuid.uuid4().hex[:8]}"
        workflow = Workflow(name=unique_name)
        test_database_session.add(workflow)
        test_database_session.commit()
        
        # created_at and updated_at should be set
        assert workflow.created_at is not None
        assert workflow.updated_at is not None
        assert isinstance(workflow.created_at, datetime)
        assert isinstance(workflow.updated_at, datetime)

    def test_timestamps_update(self, test_database_session):
        """Update işleminde updated_at timestamp'inin güncellenmesini test eder"""
        unique_name = f"Test Workflow Update {uuid.uuid4().hex[:8]}"
        workflow = Workflow(name=unique_name)
        test_database_session.add(workflow)
        test_database_session.commit()
        
        original_updated_at = workflow.updated_at
        
        # Update the workflow
        workflow.description = "Updated description"
        test_database_session.commit()
        
        # updated_at should be different
        assert workflow.updated_at != original_updated_at

    def test_repr_method(self, test_database_session):
        """__repr__ metodunu test eder"""
        unique_name = f"Test Workflow Repr {uuid.uuid4().hex[:8]}"
        workflow = Workflow(name=unique_name)
        test_database_session.add(workflow)
        test_database_session.commit()
        
        repr_str = repr(workflow)
        assert f"<Workflow(id={workflow.id})>" == repr_str

    def test_to_dict_basic_fields(self, test_database_session):
        """to_dict() metodunun basic field'ları test eder"""
        unique_name = f"Test Workflow ToDict {uuid.uuid4().hex[:8]}"
        workflow = Workflow(
            name=unique_name,
            description="Test description",
            status=WorkflowStatus.ACTIVE,
            priority=1
        )
        test_database_session.add(workflow)
        test_database_session.commit()
        
        result = workflow.to_dict()
        
        assert result['name'] == unique_name
        assert result['description'] == "Test description"
        assert result['status'] == "active"  # Enum should be converted to value
        assert result['priority'] == 1

    def test_to_dict_datetime_conversion(self, test_database_session):
        """to_dict() metodunun datetime dönüşümünü test eder"""
        unique_name = f"Test Workflow DateTime {uuid.uuid4().hex[:8]}"
        workflow = Workflow(name=unique_name)
        test_database_session.add(workflow)
        test_database_session.commit()
        
        result = workflow.to_dict()
        
        # Datetime fields should be converted to ISO format
        assert isinstance(result['created_at'], str)
        assert isinstance(result['updated_at'], str)
        assert 'T' in result['created_at']  # ISO format check
        assert 'T' in result['updated_at']  # ISO format check

    def test_to_dict_enum_conversion(self, test_database_session):
        """to_dict() metodunun enum dönüşümünü test eder"""
        unique_name = f"Test Workflow Enum {uuid.uuid4().hex[:8]}"
        workflow = Workflow(
            name=unique_name,
            status=WorkflowStatus.DRAFT
        )
        test_database_session.add(workflow)
        test_database_session.commit()
        
        result = workflow.to_dict()
        
        # Enum should be converted to its value
        assert result['status'] == "draft"
        assert not isinstance(result['status'], WorkflowStatus)


class TestWorkflowModel:
    """Workflow model testleri"""

    def test_workflow_creation(self, test_database_session, sample_workflow_data):
        """Workflow oluşturulmasını test eder"""
        # Make workflow name unique
        sample_workflow_data = sample_workflow_data.copy()
        sample_workflow_data['name'] = f"Test Workflow Creation {uuid.uuid4().hex[:8]}"
        workflow = Workflow(**sample_workflow_data)
        test_database_session.add(workflow)
        test_database_session.commit()
        
        assert workflow.id is not None
        assert workflow.name == sample_workflow_data["name"]
        assert workflow.description == sample_workflow_data["description"]
        assert workflow.status.value == sample_workflow_data["status"]
        assert workflow.priority == sample_workflow_data["priority"]

    def test_workflow_default_values(self, test_database_session):
        """Workflow default değerlerini test eder"""
        unique_name = f"Test Workflow Default {uuid.uuid4().hex[:8]}"
        workflow = Workflow(name=unique_name)
        test_database_session.add(workflow)
        test_database_session.commit()
        
        assert workflow.status == WorkflowStatus.DRAFT
        assert workflow.priority == 0

    def test_workflow_unique_name_constraint(self, test_database_session):
        """Workflow name unique constraint test eder"""
        unique_name = f"Unique Name {uuid.uuid4().hex[:8]}"
        workflow1 = Workflow(name=unique_name)
        workflow2 = Workflow(name=unique_name)  # Same name to test constraint
        
        test_database_session.add(workflow1)
        test_database_session.commit()
        
        test_database_session.add(workflow2)
        
        # Should raise IntegrityError due to unique constraint
        with pytest.raises(IntegrityError):
            test_database_session.commit()

    def test_workflow_relationships(self, workflow_with_nodes):
        """Workflow relationship'lerini test eder"""
        workflow = workflow_with_nodes["workflow"]
        nodes = workflow_with_nodes["nodes"]
        
        # Workflow should have nodes
        assert len(workflow.nodes) == 2
        assert workflow.nodes[0].name == "Node 1"
        assert workflow.nodes[1].name == "Node 2"
        
        # Nodes should reference the workflow
        for node in nodes:
            assert node.workflow_id == workflow.id


class TestNodeModel:
    """Node model testleri"""

    def test_node_creation(self, test_database_session, workflow_with_nodes):
        """Node oluşturulmasını test eder"""
        workflow = workflow_with_nodes["workflow"]
        script = workflow_with_nodes["script"]
        
        node = Node(
            workflow_id=workflow.id,
            script_id=script.id,
            name="Test Node",
            params={"param1": "value1"},
            max_retries=5,
            timeout_seconds=600
        )
        test_database_session.add(node)
        test_database_session.commit()
        
        assert node.id is not None
        assert node.workflow_id == workflow.id
        assert node.script_id == script.id
        assert node.name == "Test Node"
        assert node.params == {"param1": "value1"}
        assert node.max_retries == 5
        assert node.timeout_seconds == 600

    def test_node_default_values(self, test_database_session, workflow_with_nodes):
        """Node default değerlerini test eder"""
        workflow = workflow_with_nodes["workflow"]
        
        node = Node(
            workflow_id=workflow.id,
            name="Test Node"
        )
        test_database_session.add(node)
        test_database_session.commit()
        
        assert node.params == {}
        assert node.max_retries == 3
        assert node.timeout_seconds == 300

    def test_node_unique_constraint(self, test_database_session, workflow_with_nodes):
        """Node unique constraint (workflow_id + name) test eder"""
        workflow = workflow_with_nodes["workflow"]
        
        node1 = Node(workflow_id=workflow.id, name="Same Name")
        node2 = Node(workflow_id=workflow.id, name="Same Name")
        
        test_database_session.add(node1)
        test_database_session.commit()
        
        test_database_session.add(node2)
        
        # Should raise IntegrityError due to unique constraint
        with pytest.raises(IntegrityError):
            test_database_session.commit()


class TestScriptModel:
    """Script model testleri"""

    def test_script_creation(self, test_database_session, sample_script_data):
        """Script oluşturulmasını test eder"""
        # Make script name unique
        sample_script_data = sample_script_data.copy()
        sample_script_data['name'] = f"Test Script Creation {uuid.uuid4().hex[:8]}"
        script = Script(**sample_script_data)
        test_database_session.add(script)
        test_database_session.commit()
        
        assert script.id is not None
        assert script.name == sample_script_data["name"]
        assert script.description == sample_script_data["description"]
        assert script.language.value == sample_script_data["language"]
        assert script.script_path == sample_script_data["script_path"]
        assert script.input_params == sample_script_data["input_params"]
        assert script.output_params == sample_script_data["output_params"]
        assert script.test_status.value == sample_script_data["test_status"]

    def test_script_default_values(self, test_database_session):
        """Script default değerlerini test eder"""
        unique_name = f"Test Script Default {uuid.uuid4().hex[:8]}"
        script = Script(
            name=unique_name,
            script_path="/test/path.py"
        )
        test_database_session.add(script)
        test_database_session.commit()
        
        assert script.language == ScriptType.PYTHON
        assert script.input_params == {}
        assert script.output_params == {}
        assert script.test_status == ScriptTestStatus.UNTESTED

    def test_script_unique_name_constraint(self, test_database_session):
        """Script name unique constraint test eder"""
        unique_name = f"Unique Script {uuid.uuid4().hex[:8]}"
        script1 = Script(name=unique_name, script_path="/path1.py")
        script2 = Script(name=unique_name, script_path="/path2.py")  # Same name to test constraint
        
        test_database_session.add(script1)
        test_database_session.commit()
        
        test_database_session.add(script2)
        
        # Should raise IntegrityError due to unique constraint
        with pytest.raises(IntegrityError):
            test_database_session.commit()


class TestEdgeModel:
    """Edge model testleri"""

    def test_edge_creation(self, test_database_session, workflow_with_nodes):
        """Edge oluşturulmasını test eder"""
        workflow = workflow_with_nodes["workflow"]
        nodes = workflow_with_nodes["nodes"]
        
        edge = Edge(
            workflow_id=workflow.id,
            from_node_id=nodes[0].id,
            to_node_id=nodes[1].id,
            condition_type=ConditionType.SUCCESS
        )
        test_database_session.add(edge)
        test_database_session.commit()
        
        assert edge.id is not None
        assert edge.workflow_id == workflow.id
        assert edge.from_node_id == nodes[0].id
        assert edge.to_node_id == nodes[1].id
        assert edge.condition_type == ConditionType.SUCCESS

    def test_edge_default_values(self, test_database_session, workflow_with_nodes):
        """Edge default değerlerini test eder"""
        workflow = workflow_with_nodes["workflow"]
        nodes = workflow_with_nodes["nodes"]
        
        edge = Edge(
            workflow_id=workflow.id,
            from_node_id=nodes[0].id,
            to_node_id=nodes[1].id
        )
        test_database_session.add(edge)
        test_database_session.commit()
        
        assert edge.condition_type == ConditionType.SUCCESS

    def test_edge_unique_constraint(self, test_database_session, workflow_with_nodes):
        """Edge unique constraint test eder"""
        workflow = workflow_with_nodes["workflow"]
        nodes = workflow_with_nodes["nodes"]
        
        edge1 = Edge(
            workflow_id=workflow.id,
            from_node_id=nodes[0].id,
            to_node_id=nodes[1].id,
            condition_type=ConditionType.SUCCESS
        )
        edge2 = Edge(
            workflow_id=workflow.id,
            from_node_id=nodes[0].id,
            to_node_id=nodes[1].id,
            condition_type=ConditionType.SUCCESS
        )
        
        test_database_session.add(edge1)
        test_database_session.commit()
        
        test_database_session.add(edge2)
        
        # Should raise IntegrityError due to unique constraint
        with pytest.raises(IntegrityError):
            test_database_session.commit()


class TestExecutionModel:
    """Execution model testleri"""

    def test_execution_creation(self, test_database_session, workflow_with_nodes, sample_execution_data):
        """Execution oluşturulmasını test eder"""
        workflow = workflow_with_nodes["workflow"]
        
        execution = Execution(
            workflow_id=workflow.id,
            **sample_execution_data
        )
        test_database_session.add(execution)
        test_database_session.commit()
        
        assert execution.id is not None
        assert execution.workflow_id == workflow.id
        assert execution.status.value == sample_execution_data["status"]
        assert execution.pending_nodes == sample_execution_data["pending_nodes"]
        assert execution.executed_nodes == sample_execution_data["executed_nodes"]
        assert execution.results == sample_execution_data["results"]

    def test_execution_default_values(self, test_database_session, workflow_with_nodes):
        """Execution default değerlerini test eder"""
        workflow = workflow_with_nodes["workflow"]
        
        execution = Execution(workflow_id=workflow.id)
        test_database_session.add(execution)
        test_database_session.commit()
        
        assert execution.status == ExecutionStatus.PENDING
        assert execution.pending_nodes == 0
        assert execution.executed_nodes == 0
        assert execution.results == {}
        assert execution.started_at is not None
        assert execution.ended_at is None


class TestAuditLogModel:
    """AuditLog model testleri"""

    def test_audit_log_creation(self, test_database_session, sample_audit_log_data):
        """AuditLog oluşturulmasını test eder"""
        audit_log = AuditLog(**sample_audit_log_data)
        test_database_session.add(audit_log)
        test_database_session.commit()
        
        assert audit_log.id is not None
        assert audit_log.table_name == sample_audit_log_data["table_name"]
        assert audit_log.record_id == sample_audit_log_data["record_id"]
        assert audit_log.action.value == sample_audit_log_data["action"]
        assert audit_log.old_values == sample_audit_log_data["old_values"]
        assert audit_log.new_values == sample_audit_log_data["new_values"]


class TestRelationships:
    """Relationship testleri"""

    def test_workflow_node_relationship(self, workflow_with_nodes):
        """Workflow-Node relationship test eder"""
        workflow = workflow_with_nodes["workflow"]
        nodes = workflow_with_nodes["nodes"]
        
        # Forward relationship
        assert len(workflow.nodes) == 2
        
        # Backward relationship
        for node in nodes:
            assert node.workflow == workflow

    def test_script_node_relationship(self, workflow_with_nodes):
        """Script-Node relationship test eder"""
        script = workflow_with_nodes["script"]
        nodes = workflow_with_nodes["nodes"]
        
        # Forward relationship
        assert len(script.nodes) == 2
        
        # Backward relationship
        for node in nodes:
            assert node.script == script

    def test_cascade_delete_workflow_nodes(self, test_database_session, workflow_with_nodes):
        """Workflow silindiğinde node'ların da silinmesini test eder"""
        workflow = workflow_with_nodes["workflow"]
        workflow_id = workflow.id
        
        # Delete workflow
        test_database_session.delete(workflow)
        test_database_session.commit()
        
        # Nodes should be deleted as well (cascade)
        remaining_nodes = test_database_session.query(Node).filter_by(workflow_id=workflow_id).all()
        assert len(remaining_nodes) == 0