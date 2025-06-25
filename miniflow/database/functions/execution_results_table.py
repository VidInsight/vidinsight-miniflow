# functions/execution_results_table.py
from ..config import DatabaseConnection
from ..schema import ExecutionResult, Node, Execution
from ..utils import generate_uuid, generate_timestamp, safe_json_dumps, safe_json_loads
from ..exceptions import Result


def create_record(db_path_or_url, execution_id, node_id, status, result_data=None, error_message=None, started_at=None, ended_at=None):
    try:
        with DatabaseConnection(db_path_or_url) as session:
            record_id = generate_uuid()
            started_at = started_at or generate_timestamp()
            if not ended_at and status in ("success", "failed", "cancelled"):
                ended_at = generate_timestamp()

            record = ExecutionResult(
                id=record_id,
                execution_id=execution_id,
                node_id=node_id,
                status=status,
                result_data=safe_json_dumps(result_data),
                error_message=error_message,
                started_at=started_at,
                ended_at=ended_at
            )
            session.add(record)
            return Result.success({"record_id": record_id})
    except Exception as e:
        return Result.error(str(e))


def find_record(db_path_or_url, record_id):
    try:
        with DatabaseConnection(db_path_or_url) as session:
            rec = session.get(ExecutionResult, record_id)
            if not rec:
                return Result.success(None)
            return Result.success({
                "id": rec.id,
                "execution_id": rec.execution_id,
                "node_id": rec.node_id,
                "status": rec.status,
                "result_data": safe_json_loads(rec.result_data),
                "error_message": rec.error_message,
                "started_at": rec.started_at,
                "ended_at": rec.ended_at
            })
    except Exception as e:
        return Result.error(str(e))


def delete_record(db_path_or_url, record_id):
    try:
        with DatabaseConnection(db_path_or_url) as session:
            rec = session.get(ExecutionResult, record_id)
            if not rec:
                return Result.error(f"Record not found: {record_id}")
            session.delete(rec)
            return Result.success({"deleted": True, "record_id": record_id})
    except Exception as e:
        return Result.error(str(e))


def list_execution_records(db_path_or_url, execution_id):
    try:
        with DatabaseConnection(db_path_or_url) as session:
            records = (
                session.query(ExecutionResult)
                .join(Node, ExecutionResult.node_id == Node.id)
                .filter(ExecutionResult.execution_id == execution_id)
                .order_by(ExecutionResult.started_at.asc())
                .all()
            )
            result = [{

                "id": r.id,
                "node_id": r.node_id,
                "status": r.status,
                "result_data": safe_json_loads(r.result_data),
                "error_message": r.error_message,
                "started_at": r.started_at,
                "ended_at": r.ended_at,
                "node_name": r.node.name,
                "node_type": r.node.type
            } for r in records]
            return Result.success(result)
    except Exception as e:
        return Result.error(str(e))


def delete_execution_records(db_path_or_url, execution_id):
    try:
        with DatabaseConnection(db_path_or_url) as session:
            count = session.query(ExecutionResult).filter_by(execution_id=execution_id).delete()
            return Result.success({"deleted": True, "execution_id": execution_id, "deleted_count": count})
    except Exception as e:
        return Result.error(str(e))


def combine_execution_records_results(db_path_or_url, execution_id):
    try:
        with DatabaseConnection(db_path_or_url) as session:
            records = session.query(ExecutionResult).filter_by(execution_id=execution_id).all()
            execution = session.get(Execution, execution_id)
            if not execution:
                return Result.error(f"Execution not found: {execution_id}")
            node_ids = [n.id for n in execution.workflow.nodes]

            combined = {}
            executed_nodes = set()
            for r in records:
                executed_nodes.add(r.node_id)
                combined[r.node_id] = {
                    "status": r.status,
                    "result": safe_json_loads(r.result_data) if r.status == "success" else None,
                    "error": r.error_message if r.status == "failed" else None,
                    "timestamp": r.ended_at or r.started_at
                }

            for node_id in node_ids:
                if node_id not in executed_nodes:
                    combined[node_id] = {
                        "status": "skipped",
                        "result": None,
                        "error": None,
                        "timestamp": None
                    }

            return Result.success(combined)
    except Exception as e:
        return Result.error(str(e))


def get_record_status(db_path_or_url, record_id):
    try:
        with DatabaseConnection(db_path_or_url) as session:
            r = session.get(ExecutionResult, record_id)
            if not r:
                return Result.error(f"Record not found: {record_id}")
            return Result.success({
                "status": r.status,
                "started_at": r.started_at,
                "ended_at": r.ended_at
            })
    except Exception as e:
        return Result.error(str(e))


def get_record_timestamp(db_path_or_url, record_id):
    try:
        with DatabaseConnection(db_path_or_url) as session:
            r = session.get(ExecutionResult, record_id)
            if not r:
                return Result.error(f"Record not found: {record_id}")
            return Result.success({
                "started_at": r.started_at,
                "ended_at": r.ended_at
            })
    except Exception as e:
        return Result.error(str(e))
