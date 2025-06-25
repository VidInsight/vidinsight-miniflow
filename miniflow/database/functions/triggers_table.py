# functions/triggers_table.py
from ..config import DatabaseConnection
from ..schema import Trigger, Workflow
from ..utils import generate_uuid, safe_json_dumps, safe_json_loads
from ..exceptions import Result


def create_trigger(db_path_or_url, workflow_id, trigger_type, config=None, is_active=True):
    try:
        with DatabaseConnection(db_path_or_url) as session:
            workflow = session.get(Workflow, workflow_id)
            if not workflow:
                return Result.error(f"Workflow not found: {workflow_id}")

            trigger = Trigger(
                id=generate_uuid(),
                workflow_id=workflow_id,
                trigger_type=trigger_type,
                config=safe_json_dumps(config),
                is_active=int(is_active)
            )
            session.add(trigger)
            return Result.success({"trigger_id": trigger.id})
    except Exception as e:
        return Result.error(str(e))


def get_trigger(db_path_or_url, trigger_id):
    try:
        with DatabaseConnection(db_path_or_url) as session:
            trigger = session.get(Trigger, trigger_id)
            if not trigger:
                return Result.success(None)
            return Result.success({
                "id": trigger.id,
                "workflow_id": trigger.workflow_id,
                "trigger_type": trigger.trigger_type,
                "config": safe_json_loads(trigger.config),
                "is_active": bool(trigger.is_active)
            })
    except Exception as e:
        return Result.error(str(e))


def delete_trigger(db_path_or_url, trigger_id):
    try:
        with DatabaseConnection(db_path_or_url) as session:
            trigger = session.get(Trigger, trigger_id)
            if not trigger:
                return Result.error(f"Trigger not found: {trigger_id}")
            session.delete(trigger)
            return Result.success({"deleted": True, "trigger_id": trigger_id})
    except Exception as e:
        return Result.error(str(e))


def list_triggers(db_path_or_url):
    try:
        with DatabaseConnection(db_path_or_url) as session:
            triggers = session.query(Trigger).all()
            result = [{

                "id": t.id,
                "workflow_id": t.workflow_id,
                "trigger_type": t.trigger_type,
                "config": safe_json_loads(t.config),
                "is_active": bool(t.is_active)
            } for t in triggers]
            return Result.success(result)
    except Exception as e:
        return Result.error(str(e))


def list_workflow_triggers(db_path_or_url, workflow_id):
    try:
        with DatabaseConnection(db_path_or_url) as session:
            if not session.get(Workflow, workflow_id):
                return Result.error(f"Workflow not found: {workflow_id}")
            triggers = session.query(Trigger).filter_by(workflow_id=workflow_id).all()
            result = [{
                "id": t.id,
                "trigger_type": t.trigger_type,
                "config": safe_json_loads(t.config),
                "is_active": bool(t.is_active)
            } for t in triggers]
            return Result.success(result)
    except Exception as e:
        return Result.error(str(e))


def delete_workflow_triggers(db_path_or_url, workflow_id):
    try:
        with DatabaseConnection(db_path_or_url) as session:
            count = session.query(Trigger).filter_by(workflow_id=workflow_id).delete()
            return Result.success({"deleted_count": count})
    except Exception as e:
        return Result.error(str(e))


def get_trigger_type(db_path_or_url, trigger_id):
    try:
        with DatabaseConnection(db_path_or_url) as session:
            trigger = session.get(Trigger, trigger_id)
            if not trigger:
                return Result.error(f"Trigger not found: {trigger_id}")
            return Result.success(trigger.trigger_type)
    except Exception as e:
        return Result.error(str(e))


def update_trigger(db_path_or_url, trigger_id, new_config):
    try:
        with DatabaseConnection(db_path_or_url) as session:
            trigger = session.get(Trigger, trigger_id)
            if not trigger:
                return Result.error(f"Trigger not found: {trigger_id}")
            trigger.config = safe_json_dumps(new_config)
            return Result.success({"updated": True})
    except Exception as e:
        return Result.error(str(e))


def activate_trigger(db_path_or_url, trigger_id):
    try:
        with DatabaseConnection(db_path_or_url) as session:
            trigger = session.get(Trigger, trigger_id)
            if not trigger:
                return Result.error(f"Trigger not found: {trigger_id}")
            trigger.is_active = 1
            return Result.success({"activated": True})
    except Exception as e:
        return Result.error(str(e))


def deactivate_trigger(db_path_or_url, trigger_id):
    try:
        with DatabaseConnection(db_path_or_url) as session:
            trigger = session.get(Trigger, trigger_id)
            if not trigger:
                return Result.error(f"Trigger not found: {trigger_id}")
            trigger.is_active = 0
            return Result.success({"deactivated": True})
    except Exception as e:
        return Result.error(str(e))
