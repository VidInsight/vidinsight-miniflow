from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any

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
            raise ValueError(f"Workflow with name '{workflow_data.get('name')}' already exists")

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
            raise ValueError(f"Cannot delete workflow with active executions. Found {len(active_executions)} active executions.")
        
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
                raise ValueError(f"Workflow with name '{workflow_data['name']}' already exists")
        
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
            raise ValueError("Script name is required for node creation")
        
        script = self.script_crud.find_by_name(session, script_name)
        if not script:
            raise ValueError(f"Script with name '{script_name}' not found")
        
        node_data.pop("script_name")
        node_data["script_id"] = script.id

        # 3. Workflow içinde aynı isimli bir node var mı kontrol et
        existing_node = self.node_crud.get_by_name(session, node_data.get('name'), workflow.id)
        if existing_node:
            raise ValueError(f"Node with name '{node_data.get('name')}' already exists in workflow")
        
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
                raise ValueError(f"Node with name '{node_data['name']}' already exists in workflow")
        
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
            raise ValueError("Nodes must be in the same workflow")
        
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
                raise ValueError("Nodes must be in the same workflow")
        
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
            "success": True,
            "workflow_id": workflow.id,
            "nodes_created": len(node_ids),
            "edges_created": len(edge_ids),
            "triggers_created": len(trigger_ids),
            "workflow_name": workflow.name
        }

    def delete_workflow(self, session: Session, workflow_id: str):
        """
        Workflow'u ve tüm bileşenlerini sil
        """
        # Private delete fonksiyonunu kullan (tüm bileşenleri siler)
        deleted_workflow = self.__workflow_delete(session, workflow_id)
        
        return {
            "success": True,
            "workflow_id": deleted_workflow.id,
            "workflow_name": deleted_workflow.name,
            "message": "Workflow and all components deleted successfully"
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
        
        # AŞAMA 2: Eski workflow'u tamamen sil
        delete_result = self.delete_workflow(session, workflow_id)
        
        # AŞAMA 3: Yeni workflow'u oluştur
        create_result = self.create_workflow(session, workflow_data)
        
        # AŞAMA 4: Sonuçları döndür
        return {
            "success": True,
            "operation": "update_via_delete_create",
            "old_workflow": {
                "id": workflow_id,
                "name": old_workflow_name,
                "status": "deleted"
            },
            "new_workflow": {
                "id": create_result["workflow_id"],
                "name": create_result["workflow_name"],
                "status": "created"
            },
            "components_created": {
                "nodes": create_result["nodes_created"],
                "edges": create_result["edges_created"],
                "triggers": create_result["triggers_created"]
            },
            "message": f"Workflow updated successfully - old workflow '{old_workflow_name}' deleted, new workflow '{create_result['workflow_name']}' created",
            "warning": "Workflow ID changed because workflow was completely recreated"
        }
    

    # SCRIPT FUNCTIONS
    # ==============================================================
    def __script_create(self, session: Session, **script_data):
        # 1. Aynı isimli bir script var mı kontrol et
        if self.script_crud.check_name_exists(session, script_data['name']):
            raise ValueError(f"Script with name '{script_data.get('name')}' already exists")

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
                raise ValueError(f"Script with name '{script_data['name']}' already exists")
        
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
            raise ValueError(f"Cannot delete script '{old_script.name}' - it is used by nodes: {', '.join(node_names)}")
        
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


    # END-TO-END SCRIPT FUNCTIONS
    # ==============================================================
    def create_script(self, session: Session, script_data: dict):
        """
        Yeni script oluştur
        """
        script = self.__script_create(session, **script_data)
        
        return {
            "success": True,
            "script_id": script.id,
            "script_name": script.name,
            "message": "Script created successfully"
        }

    def update_script(self, session: Session, script_id: str, script_data: dict):
        """
        Script'i güncelle
        """
        script = self.__script_update(session, script_id, **script_data)
        
        return {
            "success": True,
            "script_id": script.id,
            "script_name": script.name,
            "message": "Script updated successfully"
        }

    def delete_script(self, session: Session, script_id: str):
        """
        Script'i sil - Usage kontrolü ile
        """
        deleted_script = self.__script_delete(session, script_id)
        
        return {
            "success": True,
            "script_id": deleted_script.id,
            "script_name": deleted_script.name,
            "message": "Script deleted successfully"
        }

    def get_script_usage(self, session: Session, script_id: str):
        """
        Script'in hangi workflow/node'larda kullanıldığını getir
        """
        # 1. Script'i bul
        script = self.script_crud.find_by_id(session, script_id)
        
        # 2. Bu script'i kullanan node'ları bul
        nodes_using_script = self.node_crud.get_nodes_by_script(session, script_id)
        
        # 3. Node'ların workflow bilgilerini topla
        workflow_usage = {}
        for node in nodes_using_script:
            workflow_id = node.workflow_id
            if workflow_id not in workflow_usage:
                workflow = self.workflow_crud.find_by_id(session, workflow_id)
                workflow_usage[workflow_id] = {
                    "workflow_id": workflow_id,
                    "workflow_name": workflow.name,
                    "nodes": []
                }
            
            workflow_usage[workflow_id]["nodes"].append({
                "node_id": node.id,
                "node_name": node.name
            })
        
        return {
            "success": True,
            "script_id": script.id,
            "script_name": script.name,
            "usage": {
                "total_nodes": len(nodes_using_script),
                "total_workflows": len(workflow_usage),
                "workflows": list(workflow_usage.values())
            }
        }