# functions/executions_table.py
from ..config import DatabaseConnection
from ..schema import Execution, Workflow
from ..utils import generate_uuid, generate_timestamp, safe_json_dumps
from ..exceptions import Result


def create_execution(db_path_or_url, workflow_id):
    try:
        with DatabaseConnection(db_path_or_url) as session:
            workflow = session.get(Workflow, workflow_id)
            if not workflow:
                return Result.error(f"Workflow not found: {workflow_id}")

            execution_id = generate_uuid()
            now = generate_timestamp()
            execution = Execution(
                id=execution_id,
                workflow_id=workflow_id,
                status="pending",
                results="{}",
                started_at=now,
                ended_at=now
            )
            session.add(execution)
            return Result.success({"execution_id": execution_id})
    except Exception as e:
        return Result.error(str(e))


def get_execution(db_path_or_url, execution_id):
    try:
        with DatabaseConnection(db_path_or_url) as session:
            execution = session.get(Execution, execution_id)
            if not execution:
                return Result.success(None)
            return Result.success({
                "id": execution.id,
                "workflow_id": execution.workflow_id,
                "status": execution.status,
                "results": execution.results,
                "started_at": execution.started_at,
                "ended_at": execution.ended_at
            })
    except Exception as e:
        return Result.error(str(e))


def delete_execution(db_path_or_url, execution_id):
    try:
        with DatabaseConnection(db_path_or_url) as session:
            execution = session.get(Execution, execution_id)
            if not execution:
                return Result.error(f"Execution not found: {execution_id}")
            session.delete(execution)
            return Result.success({"deleted": True, "execution_id": execution_id})
    except Exception as e:
        return Result.error(str(e))


def list_executions(db_path_or_url, workflow_id=None, status=None, limit=100, offset=0):
    try:
        with DatabaseConnection(db_path_or_url) as session:
            query = session.query(Execution)
            if workflow_id:
                query = query.filter(Execution.workflow_id == workflow_id)
            if status:
                query = query.filter(Execution.status == status)
            executions = query.order_by(Execution.started_at.desc()).offset(offset).limit(limit).all()

            result = [{

                "id": e.id,
                "workflow_id": e.workflow_id,
                "status": e.status,
                "results": e.results,
                "started_at": e.started_at,
                "ended_at": e.ended_at
            } for e in executions]
            return Result.success(result)
    except Exception as e:
        return Result.error(str(e))


def set_execution_end_time(db_path_or_url, execution_id, ended_at):
    try:
        with DatabaseConnection(db_path_or_url) as session:
            execution = session.get(Execution, execution_id)
            if not execution:
                return Result.error(f"Execution not found: {execution_id}")
            execution.ended_at = ended_at
            return Result.success({"updated": True, "execution_id": execution_id})
    except Exception as e:
        return Result.error(str(e))


def set_execution_status(db_path_or_url, execution_id, new_status):
    try:
        with DatabaseConnection(db_path_or_url) as session:
            execution = session.get(Execution, execution_id)
            if not execution:
                return Result.error(f"Execution not found: {execution_id}")
            execution.status = new_status
            return Result.success({"updated": True, "execution_id": execution_id, "status": new_status})
    except Exception as e:
        return Result.error(str(e))


def set_execution_result(db_path_or_url, execution_id, result_dict):
    try:
        with DatabaseConnection(db_path_or_url) as session:
            execution = session.get(Execution, execution_id)
            if not execution:
                return Result.error(f"Execution not found: {execution_id}")
            execution.results = safe_json_dumps(result_dict)
            return Result.success({"updated": True, "execution_id": execution_id})
    except Exception as e:
        return Result.error(str(e))


def start_execution(db_path_or_url, execution_id):
    try:
        with DatabaseConnection(db_path_or_url) as session:
            execution = session.get(Execution, execution_id)
            if not execution:
                return Result.error(f"Execution not found: {execution_id}")
            execution.status = "running"
            execution.started_at = generate_timestamp()
            return Result.success({"execution_id": execution_id, "status": "running"})
    except Exception as e:
        return Result.error(str(e))


def stop_execution(db_path_or_url, execution_id):
    try:
        with DatabaseConnection(db_path_or_url) as session:
            execution = session.get(Execution, execution_id)
            if not execution:
                return Result.error(f"Execution not found: {execution_id}")
            execution.status = "stopped"
            execution.ended_at = generate_timestamp()
            return Result.success({"execution_id": execution_id, "status": "stopped"})
    except Exception as e:
        return Result.error(str(e))


def check_execution_completion(db_path_or_url, execution_id):
    try:
        with DatabaseConnection(db_path_or_url) as session:
            execution = session.get(Execution, execution_id)
            if not execution:
                return Result.error(f"Execution not found: {execution_id}")
            completed = execution.status in ("completed", "failed", "cancelled")
            return Result.success({"completed": completed, "status": execution.status})
    except Exception as e:
        return Result.error(str(e))
