from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime

from .crud import (
    WorkflowCRUD, NodeCRUD, EdgeCRUD, TriggerCRUD, 
    ScriptCRUD, ExecutionCRUD,ExecutionInputCRUD, 
    ExecutionOutputCRUD, ArchivedExecutionCRUD,
    AuditLogCRUD
)
from .models import (
    Workflow, Node, Edge, Trigger, Script, Execution, 
    ExecutionInput, ExecutionOutput, ArchivedExecution, AuditLog,
    WorkflowStatus, ExecutionStatus, TriggerType, ConditionType, AuditAction
)
from ..exceptions import ValidationError, BusinessLogicError

class DatabaseOrchestration:
    def __init__(self):
        self.workflow_crud = WorkflowCRUD()
        self.node_crud = NodeCRUD()
        self.edge_crud = EdgeCRUD()
        self.trigger_crud = TriggerCRUD()
        self.script_crud = ScriptCRUD()
        self.execution_crud = ExecutionCRUD()
        self.execution_input_crud = ExecutionInputCRUD()
        self.execution_output_crud = ExecutionOutputCRUD()
        self.archived_execution_crud = ArchivedExecutionCRUD()
        self.audit_log_crud = AuditLogCRUD()


    # WORKFLOW FUNCTIONS
    # ==============================================================
    def __workflow_create(self, session: Session, **workflow_data):
        # 1. Aynı isimli bir workflow var mı kontrol et
        if self.workflow_crud.check_name_exists(session, workflow_data['name']):
            raise ValidationError(f"Workflow with name '{workflow_data.get('name')}' already exists")

        # 2. Workflow oluştur
        workflow = self.workflow_crud.create(session, **workflow_data)

        # 3. Audit Log ekle
        self.audit_log_crud.log_action(
            session=session,
            table_name="workflow",
            record_id=workflow.id,
            action=AuditAction.CREATE,
            new_values=workflow.to_dict()
        )

        # 4. Oluşan workflow'u döndür
        return workflow

    def __workflow_delete(self, session: Session, workflow_id):
        # 1. Workflow'u bul
        old_workflow = self.workflow_crud.find_by_id(session, workflow_id)

        # 2. Active Executionları kontorl et
        active_executions = self.execution_crud.get_active_executions_by_workflow(session, workflow_id)
        if active_executions:
            raise BusinessLogicError(f"Cannot delete workflow with active executions. Found {len(active_executions)} active executions.")
        
        # 3. İlişkili bileşenleri sil (CASCADE yoksa manuel)
        # 3a. Trigger'ları sil
        existing_triggers = self.trigger_crud.get_triggers_by_workflow(session, workflow_id)
        for trigger in existing_triggers:
            self.__trigger_delete(session, trigger.id)
        
        # 3b. Edge'leri sil
        existing_edges = self.edge_crud.get_edges_by_workflow(session, workflow_id)
        for edge in existing_edges:
            self.__edge_delete(session, edge.id)
        
        # 3c. Node'ları sil
        existing_nodes = self.node_crud.get_nodes_by_workflow(session, workflow_id)
        for node in existing_nodes:
            self.__node_delete(session, node.id)
        
        # 4. Workflow'u sil
        result = self.workflow_crud.delete(session, workflow_id)

        # 5. Audit log ekle
        self.audit_log_crud.log_action(
            session=session,
            table_name="workflow",
            record_id=old_workflow.id,
            action=AuditAction.DELETE,
            old_values=old_workflow.to_dict()
        )

        # 6. Silinen workflow'u döndür
        return old_workflow

    def __workflow_update(self, session: Session, workflow_id, **workflow_data):
        # 1. Eski değerleri al
        old_workflow = self.workflow_crud.find_by_id(session, workflow_id)

        # 2. İsim değişikliği varsa kontrol et
        if workflow_data['name'] != old_workflow.name:
            if self.workflow_crud.check_name_exists(session, workflow_data['name']):
                raise ValidationError(f"Workflow with name '{workflow_data['name']}' already exists")
        
        # 3. Workflow'u güncelle
        updated_workflow = self.workflow_crud.update(session, workflow_id, **workflow_data)

        # 4. Audit Log ekle
        self.audit_log_crud.log_action(
            session=session,
            table_name='workflow',
            record_id=updated_workflow.id,
            action=AuditAction.UPDATE,
            old_values=old_workflow.to_dict(),
            new_values=updated_workflow.to_dict()
        )

        # 5. Updated workflow'u döndür
        return updated_workflow

    # NODE FUNCTIONS
    # ==============================================================
    def __node_create(self, session: Session, **node_data):
        # 1. Workflw'un valığını kontrol et
        workflow = self.workflow_crud.find_by_id(session, node_data.get('workflow_id'))

        # 2. Script'in varlığını kontrol et ve ID'yi bul
        script_name = node_data.get("script_name")
        if not script_name:
            raise ValidationError("Script name is required for node creation")
        
        script = self.script_crud.find_by_name(session, script_name)
        if not script:
            raise BusinessLogicError(f"Script with name '{script_name}' not found")
        
        node_data.pop("script_name")
        node_data["script_id"] = script.id

        # 3. Workflow içinde aynı isimli bir node var mı kontrol et
        existing_node = self.node_crud.get_by_name(session, node_data.get('name'), workflow.id)
        if existing_node:
            raise ValidationError(f"Node with name '{node_data.get('name')}' already exists in workflow")
        
        # 4. Node oluştur
        node = self.node_crud.create(session, **node_data)

        # 5. Audit Log Ekle
        self.audit_log_crud.log_action(
            session=session,
            table_name="node",
            record_id=node.id,
            action=AuditAction.CREATE,
            new_values=node.to_dict()
        )

        # 6. Node değerini döndür
        return node

    def __node_delete(self, session: Session, node_id):
        # 1. Node'u bul
        old_node = self.node_crud.find_by_id(session, node_id)
        
        # 2. Node'u sil
        result = self.node_crud.delete(session, node_id)

        # 3. Audit log ekle
        self.audit_log_crud.log_action(
            session=session,
            table_name="node",
            record_id=old_node.id,
            action=AuditAction.DELETE,
            old_values=old_node.to_dict()
        )

        # 4. Silinen node'u döndür
        return old_node

    def __node_update(self, session: Session, node_id, **node_data):
        # 1. Eski değerleri al
        old_node = self.node_crud.find_by_id(session, node_id)

        # 2. İsim değişikliği varsa kontrol et
        if 'name' in node_data and node_data['name'] != old_node.name:
            existing_node = self.node_crud.get_by_name(session, node_data['name'], old_node.workflow_id)
            if existing_node and existing_node.id != node_id:
                raise ValidationError(f"Node with name '{node_data['name']}' already exists in workflow")
        
        # 3. Node'u güncelle
        updated_node = self.node_crud.update(session, node_id, **node_data)

        # 4. Audit Log ekle
        self.audit_log_crud.log_action(
            session=session,
            table_name='node',
            record_id=updated_node.id,
            action=AuditAction.UPDATE,
            old_values=old_node.to_dict(),
            new_values=updated_node.to_dict()
        )

        # 5. Updated node'u döndür
        return updated_node

    # EDGE FUNCTIONS
    # ==============================================================
    def __edge_create(self, session: Session, **edge_data):
        # 1. Node'ların varlığını kontrol et
        from_node = self.node_crud.find_by_id(session, edge_data.get('from_node_id'))
        to_node = self.node_crud.find_by_id(session, edge_data.get('to_node_id'))
        
        # 2. Aynı workflow'da mı kontrol et
        if from_node.workflow_id != to_node.workflow_id:
            raise ValidationError("Nodes must be in the same workflow")
        
        # 3. Workflow ID'yi ayarla
        edge_data['workflow_id'] = from_node.workflow_id

        # 4. Edge oluştur
        edge = self.edge_crud.create(session, **edge_data)

        # 5. Audit log ekle
        self.audit_log_crud.log_action(
            session=session,
            table_name="edge",
            record_id=edge.id,
            action=AuditAction.CREATE,
            new_values=edge.to_dict()
        )

        # 6. Edge'i döndür
        return edge

    def __edge_delete(self, session: Session, edge_id):
        # 1. Edge'i bul
        old_edge = self.edge_crud.find_by_id(session, edge_id)
        
        # 2. Edge'i sil
        result = self.edge_crud.delete(session, edge_id)

        # 3. Audit log ekle
        self.audit_log_crud.log_action(
            session=session,
            table_name="edge",
            record_id=old_edge.id,
            action=AuditAction.DELETE,
            old_values=old_edge.to_dict()
        )

        # 4. Silinen edge'i döndür
        return old_edge

    def __edge_update(self, session: Session, edge_id, **edge_data):
        # 1. Eski değerleri al
        old_edge = self.edge_crud.find_by_id(session, edge_id)

        # 2. Node ID'leri değişiyorsa kontrol et
        if 'from_node_id' in edge_data or 'to_node_id' in edge_data:
            from_node_id = edge_data.get('from_node_id', old_edge.from_node_id)
            to_node_id = edge_data.get('to_node_id', old_edge.to_node_id)
            
            from_node = self.node_crud.find_by_id(session, from_node_id)
            to_node = self.node_crud.find_by_id(session, to_node_id)
            
            if from_node.workflow_id != to_node.workflow_id:
                raise ValidationError("Nodes must be in the same workflow")
        
        # 3. Edge'i güncelle
        updated_edge = self.edge_crud.update(session, edge_id, **edge_data)

        # 4. Audit Log ekle
        self.audit_log_crud.log_action(
            session=session,
            table_name='edge',
            record_id=updated_edge.id,
            action=AuditAction.UPDATE,
            old_values=old_edge.to_dict(),
            new_values=updated_edge.to_dict()
        )

        # 5. Updated edge'i döndür
        return updated_edge

    # TRIGGER FUNCTIONS
    # ==============================================================
    def __trigger_create(self, session: Session, **trigger_data):
        # 1. Workflow'un varlığını kontrol et
        workflow = self.workflow_crud.find_by_id(session, trigger_data.get('workflow_id'))

        # 2. Trigger oluştur
        trigger = self.trigger_crud.create(session, **trigger_data)

        # 3. Audit Log ekle
        self.audit_log_crud.log_action(
            session=session,
            table_name="trigger",
            record_id=trigger.id,
            action=AuditAction.CREATE,
            new_values=trigger.to_dict()
        )

        # 4. Trigger'ı döndür
        return trigger

    def __trigger_delete(self, session: Session, trigger_id):
        # 1. Trigger'ı bul
        old_trigger = self.trigger_crud.find_by_id(session, trigger_id)
        
        # 2. Trigger'ı sil
        result = self.trigger_crud.delete(session, trigger_id)

        # 3. Audit log ekle
        self.audit_log_crud.log_action(
            session=session,
            table_name="trigger",
            record_id=old_trigger.id,
            action=AuditAction.DELETE,
            old_values=old_trigger.to_dict()
        )

        # 4. Silinen trigger'ı döndür
        return old_trigger

    def __trigger_update(self, session: Session, trigger_id, **trigger_data):
        # 1. Eski değerleri al
        old_trigger = self.trigger_crud.find_by_id(session, trigger_id)

        # 2. Trigger'ı güncelle
        updated_trigger = self.trigger_crud.update(session, trigger_id, **trigger_data)

        # 3. Audit Log ekle
        self.audit_log_crud.log_action(
            session=session,
            table_name='trigger',
            record_id=updated_trigger.id,
            action=AuditAction.UPDATE,
            old_values=old_trigger.to_dict(),
            new_values=updated_trigger.to_dict()
        )

        # 4. Updated trigger'ı döndür
        return updated_trigger

    # SCRIPT FUNCTIONS
    # ==============================================================
    def __script_create(self, session: Session, **script_data):
        # 1. Aynı isimli bir script var mı kontrol et
        if self.script_crud.check_name_exists(session, script_data['name']):
            raise ValidationError(f"Script with name '{script_data.get('name')}' already exists")

        # 2. Script oluştur
        script = self.script_crud.create(session, **script_data)

        # 3. Audit Log ekle
        self.audit_log_crud.log_action(
            session=session,
            table_name="script",
            record_id=script.id,
            action=AuditAction.CREATE,
            new_values=script.to_dict()
        )

        # 4. Oluşan script'i döndür
        return script

    def __script_update(self, session: Session, script_id, **script_data):
        # 1. Eski değerleri al
        old_script = self.script_crud.find_by_id(session, script_id)

        # 2. İsim değişikliği varsa kontrol et
        if 'name' in script_data and script_data['name'] != old_script.name:
            if self.script_crud.check_name_exists(session, script_data['name']):
                raise ValidationError(f"Script with name '{script_data['name']}' already exists")
        
        # 3. Script'i güncelle
        updated_script = self.script_crud.update(session, script_id, **script_data)

        # 4. Audit Log ekle
        self.audit_log_crud.log_action(
            session=session,
            table_name='script',
            record_id=updated_script.id,
            action=AuditAction.UPDATE,
            old_values=old_script.to_dict(),
            new_values=updated_script.to_dict()
        )

        # 5. Updated script'i döndür
        return updated_script

    def __script_delete(self, session: Session, script_id):
        # 1. Script'i bul
        old_script = self.script_crud.find_by_id(session, script_id)

        # 2. Script'in kullanıldığı node'ları kontrol et
        nodes_using_script = self.node_crud.get_nodes_by_script(session, script_id)
        if nodes_using_script:
            node_names = [node.name for node in nodes_using_script]
            raise BusinessLogicError(f"Cannot delete script '{old_script.name}' - it is used by nodes: {', '.join(node_names)}")
        
        # 3. Script'i sil
        result = self.script_crud.delete(session, script_id)

        # 4. Audit log ekle
        self.audit_log_crud.log_action(
            session=session,
            table_name="script",
            record_id=old_script.id,
            action=AuditAction.DELETE,
            old_values=old_script.to_dict()
        )

        # 5. Silinen script'i döndür
        return old_script

    # ==============================================================
    # END-TO-END WORKFLOW FUNCTIONS
    # ==============================================================
    def create_workflow(self, session: Session, workflow_data: dict):
        nodes = workflow_data["nodes"]
        edges = workflow_data["edges"]
        triggers = workflow_data["triggers"]
        
        # 1. Workflow oluştur
        workflow = self.__workflow_create(session, **{'name':workflow_data["name"], 'description':workflow_data["description"]})

        # 2. Node'ları oluştur
        node_ids = {}
        for i, node_data in enumerate(nodes):
            node_data["workflow_id"] = workflow.id
            node = self.__node_create(session, **node_data)
            node_ids[node.name] = node.id

        # 3. Edge'leri oluştur
        edge_ids = []
        for i, edge_data in enumerate(edges):  
            from_node_name = edge_data["from_node"]
            to_node_name = edge_data["to_node"]
            
            # Edge data'yı hazırla
            edge_create_data = {
                "from_node_id": node_ids[from_node_name],
                "to_node_id": node_ids[to_node_name],
                "condition_type": ConditionType(edge_data.get("condition_type", "success"))
            }
            
            # Private edge create fonksiyonunu kullan
            edge = self.__edge_create(session, **edge_create_data)
            edge_ids.append(edge.id)

        # 4. Trigger'ları oluştur
        trigger_ids = []
        for i, trigger_data in enumerate(triggers):
            # Trigger data'yı hazırla
            trigger_create_data = {
                "workflow_id": workflow.id,
                "trigger_type": TriggerType(trigger_data["trigger_type"]),
                "trigger_config": trigger_data.get("config", {}),
                "is_active": trigger_data.get("is_active", True)
            }
            
            # Private trigger create fonksiyonunu kullan
            trigger = self.__trigger_create(session, **trigger_create_data)
            trigger_ids.append(trigger.id)

        # 5. Sonuçları döndür
        return {
            'workflow_id': workflow.id,
            'created_at': workflow.created_at.isoformat() if workflow.created_at else None,
            'nodes': node_ids,
            'edges': edge_ids,
            'triggers': trigger_ids,
        }

    def delete_workflow(self, session: Session, workflow_id: str):
        """
        Workflow'u ve tüm bileşenlerini sil
        """
        # Private delete fonksiyonunu kullan (tüm bileşenleri siler)
        deleted_workflow = self.__workflow_delete(session, workflow_id)
        
        return {
            "workflow_id": deleted_workflow.id,
            "workflow_name": deleted_workflow.name,
        }

    def update_workflow(self, session: Session, workflow_id: str, workflow_data: dict):
        """
        Workflow'u güncelle - DELETE + CREATE yaklaşımı
        
        1. Eski workflow'u tamamen sil (delete_workflow)
        2. Yeni workflow'u oluştur (create_workflow)
        
        NOT: Workflow ID değişecek çünkü tamamen yeniden oluşturuluyor
        """
        
        # AŞAMA 1: Eski workflow bilgilerini kaydet
        old_workflow = self.workflow_crud.find_by_id(session, workflow_id)
        old_workflow_name = old_workflow.name
        old_workflow_id = old_workflow.id
        
        # AŞAMA 2: Eski workflow'u tamamen sil
        delete_result = self.delete_workflow(session, workflow_id)
        
        # AŞAMA 3: Yeni workflow'u oluştur
        created_result = self.create_workflow(session, workflow_data)
        
        # AŞAMA 4: Sonuçları döndür (WorkflowUpdateResponse formatında)
        from datetime import datetime
        return {
            'workflow_id': created_result['workflow_id'],
            'created_at': created_result['created_at'],  # Zaten isoformat edilmiş
            'nodes': created_result['nodes'],
            'edges': created_result['edges'],
            'triggers': created_result['triggers'],
        }

    def get_workflows(self, session: Session, page: Optional[int] = None, page_size: Optional[int] = None):
        """
        Tüm workflow'ları listele
        """
        workflows = self.workflow_crud.get_all(session)
        workflow_list = [workflow.to_dict() for workflow in workflows]
            
        return workflow_list

    def get_workflow(self, session: Session, workflow_id: str):
        """
        Workflow detayını getir (nodes, edges, triggers dahil)
        """
        # 1. Workflow'u bul
        workflow = self.workflow_crud.find_by_id(session, workflow_id)
        if not workflow:
            raise BusinessLogicError(f"Workflow not found: {workflow_id}")
        
        workflow_dict = workflow.to_dict()
        
        # 2. Node'ları getir
        nodes = self.node_crud.get_nodes_by_workflow(session, workflow_id)
        workflow_dict['nodes'] = [node.to_dict() for node in nodes]
        
        # 3. Edge'leri getir
        edges = self.edge_crud.get_edges_by_workflow(session, workflow_id)
        workflow_dict['edges'] = [edge.to_dict() for edge in edges]
        
        # 4. Trigger'ları getir
        triggers = self.trigger_crud.get_triggers_by_workflow(session, workflow_id)
        workflow_dict['triggers'] = [trigger.to_dict() for trigger in triggers]
        
        return workflow_dict

    # END-TO-END SCRIPT FUNCTIONS
    # ==============================================================
    def create_script(self, session: Session, script_data: dict):
        """
        Yeni script oluştur
        """
        script = self.__script_create(session, **script_data)
        
        api_payload = {
            'script_id': script.id,
            'absolute_path': script.script_path,
            'created_at': script.created_at.isoformat() if script.created_at else None
        }

        return api_payload

    def delete_script(self, session: Session, script_id: str):
        """
        Script'i sil - Usage kontrolü ile
        """
        deleted_script = self.__script_delete(session, script_id)
        
        api_payload = {
            'script_id': deleted_script.id,
            'script_name': deleted_script.name,
        }

        return api_payload

    def get_scripts(self, session: Session):
        """
        Tüm script'leri listele
        """
        scripts = self.script_crud.get_all(session)
        script_list = [script.to_dict() for script in scripts]

        return script_list

    def get_script(self, session: Session, script_id: str, include_content: bool = False):
        """
        Script detayını getir
        """
        # 1. Script'i bul
        script = self.script_crud.find_by_id(session, script_id)
        if not script:
            raise BusinessLogicError(f"Script not found: {script_id}")
        
        script_dict = script.to_dict()
        
        # 2. Eğer content isteniyorsa, dosyadan oku
        if include_content and script.script_path:
            try:
                with open(script.script_path, 'r') as f:
                    script_dict['file_content'] = f.read()
            except Exception as e:
                script_dict['file_content'] = f"Error reading file: {str(e)}"
        
        return script_dict
    

    #  EXECUTION FUNCTIONS
    # ==============================================================
    def __execution_create(self, session: Session, **execution_data):
        """
        Execution oluştur
        """
        execution = self.execution_crud.create(session, **execution_data)
        
        self.audit_log_crud.log_action(
            session=session,
            table_name="execution",
            record_id=execution.id,
            action=AuditAction.CREATE,
            new_values=execution.to_dict()
        )

        return execution
    
    #  EXECUTION INPUTS FUNCTIONS
    # ==============================================================
    def __execution_input_create(self, session: Session, **execution_input_data):
        """
        Execution input oluştur
        """
        execution_input = self.execution_input_crud.create(session, **execution_input_data)
        
        self.audit_log_crud.log_action(
            session=session,
            table_name="execution_input",
            record_id=execution_input.id,
            action=AuditAction.CREATE,
            new_values=execution_input.to_dict()
        )       

        return execution_input
    
    def __execution_input_delete(self, session: Session, execution_input_id: str):
        deleted_input = self.execution_input_crud.delete(session, execution_input_id)
        
        self.audit_log_crud.log_action(
            session=session,
            table_name="execution_input",
            record_id=deleted_input.id,
            action=AuditAction.DELETE,
            old_values=deleted_input.to_dict()
        )

        return deleted_input

    #  EXECUTION OUTPUTS FUNCTIONS
    # ==============================================================
    def __execution_output_create(self, session: Session, **execution_output_data):
        """
        Execution output oluştur
        """
        execution_output = self.execution_output_crud.create(session, **execution_output_data)
        
        self.audit_log_crud.log_action(
            session=session,
            table_name="execution_output",
            record_id=execution_output.id,
            action=AuditAction.CREATE,
            new_values=execution_output.to_dict()
        )

        return execution_output

    def __combine_execution_results(self, session: Session, execution_id: str):
        """
        Execution'ın sonuçlarını birleştir
        """
        # Execution'ın tüm output'larını getir
        execution_outputs = self.execution_output_crud.get_execution_outputs_by_execution(session, execution_id)
        
        # Sonuçları birleştir
        combined_results = {}
        for output in execution_outputs:
            combined_results[output.node_id] = {
                'status': output.status.value if output.status else None,
                'result_data': output.result_data,
                'started_at': output.started_at.isoformat() if output.started_at else None,
                'ended_at': output.ended_at.isoformat() if output.ended_at else None
            }
        
        return combined_results


    # END-TO-END EXECUTION FUNCTIONS
    # ==============================================================
    def trigger_workflow(self, session: Session, workflow_id: str):
        """
        Workflow'u tetikle
        """
        workflow = self.workflow_crud.find_by_id(session, workflow_id)
        if not workflow:
            raise BusinessLogicError(f"Workflow not found: {workflow_id}")
        
        nodes = self.node_crud.get_nodes_by_workflow(session, workflow_id)
        if not nodes:
            raise BusinessLogicError(f"No nodes found for workflow: {workflow_id}")
        
        execution_payload = {
            'workflow_id': workflow.id,
            'status': ExecutionStatus.PENDING,
            'pending_nodes': len(nodes),
            'started_at': datetime.utcnow(),
        }

        execution = self.__execution_create(session, **execution_payload)

        input_ids = []
        for node in nodes:
            execution_input_payload = {
                'execution_id': execution.id,
                'node_id': node.id,
                'priority': workflow.priority,
                'dependency_count': self.edge_crud.get_dependency_count(session, node.id),
            }

            created_input = self.__execution_input_create(session, **execution_input_payload)
            input_ids.append(created_input.id)  # Store just the ID, not the object

        return {
            'execution_id': execution.id,
            'pending_nodes': len(nodes),
            'pending_nodes_ids': input_ids,
            'started_at': execution.started_at.isoformat() if execution.started_at else None,
        }
    
    def get_execution(self, session: Session, execution_id: str):
        """
        Execution detayını getir
        """
        # 1. Execution'i bul
        execution = self.execution_crud.find_by_id(session, execution_id)
        if not execution:
            raise BusinessLogicError(f"Execution not found: {execution_id}")
        
        execution_dict = execution.to_dict()
        
        return execution_dict


    def get_executions(self, session: Session, page: Optional[int] = None, page_size: Optional[int] = None):
        """
        Tüm execution'ları listele
        """
        executions = self.execution_crud.get_all(session)
        execution_list = [execution.to_dict() for execution in executions]

        return execution_list
    

    def cancel_execution(self, session: Session, execution_id: str):
        """
        Execution'ı iptal et
        """
        execution = self.execution_crud.find_by_id(session, execution_id)
        if not execution:
            raise BusinessLogicError(f"Execution not found: {execution_id}")
        
        execution_inputs = self.execution_input_crud.get_execution_inputs_by_execution(session, execution_id)
        execution_input_ids = []
        for input in execution_inputs:
            deleted_input = self.__execution_input_delete(session, input.id)
            execution_input_ids.append(deleted_input.id)
        

        result = self.__combine_execution_results(session, execution_id)
        for input_id in execution_input_ids:
            result[input_id] = "CANCELLED"

        execution_payload = {
            'status': ExecutionStatus.CANCELLED,
            'results': result,
            'ended_at': datetime.utcnow(),
        }
        execution = self.execution_crud.update(session, execution_id, **execution_payload)

        return {
            'execution_id': execution.id,
            'pending_nodes': execution.pending_nodes,
            'executed_nodes': execution.executed_nodes,
            'results': result,
            'started_at': execution.started_at.isoformat() if execution.started_at else None,
        }