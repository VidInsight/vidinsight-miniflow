# functions/workflow_orchestration.py
from ..config import DatabaseConnection
from ..schema import Node, Edge, ExecutionQueue, Execution, ExecutionResult
from ..exceptions import Result
from ..utils import generate_timestamp, generate_uuid, safe_json_dumps

from .execution_results_table import combine_execution_records_results
from .execution_queue_table import create_task, update_task_status
from .executions_table import (
    create_execution, set_execution_result, set_execution_status
)
from .workflows_table import create_workflow
from .nodes_table import create_node
from .edges_table import create_edge


def get_ready_tasks_for_execution(db_path_or_url, execution_id=None, limit=None):
    try:
        with DatabaseConnection(db_path_or_url) as session:
            query = session.query(ExecutionQueue).filter_by(status="ready")
            if execution_id is not None:
                query = query.filter_by(execution_id=execution_id)
            if limit is not None:
                query = query.limit(limit)
            tasks = query.all()
            result = [{
                "id": t.id,
                "execution_id": t.execution_id,
                "node_id": t.node_id,
                "priority": t.priority,
                "dependency_count": t.dependency_count
            } for t in tasks]
            return Result.success(result)
    except Exception as e:
        return Result.error(str(e))


def mark_task_as_running(db_path_or_url, task_id):
    return update_task_status(db_path_or_url, task_id, "running")


def process_execution_result(db_path_or_url, execution_id, node_id, status, result_data=None, error_message=None):
    try:
        with DatabaseConnection(db_path_or_url) as session:
            record = ExecutionResult(
                id=generate_uuid(),
                execution_id=execution_id,
                node_id=node_id,
                status=status,
                result_data=safe_json_dumps(result_data),
                error_message=error_message,
                started_at=generate_timestamp(),
                ended_at=generate_timestamp()
            )
            session.add(record)

            # Bağımlılıkları güncelle
            if status == "success":
                dependents = session.query(Edge).filter_by(from_node_id=node_id).all()
                for dep in dependents:
                    task = session.query(ExecutionQueue).filter_by(
                        execution_id=execution_id,
                        node_id=dep.to_node_id
                    ).first()
                    if task:
                        task.dependency_count = max(0, task.dependency_count - 1)
                        if task.dependency_count == 0 and task.status == "pending":
                            task.status = "ready"

            return Result.success({"record_id": record.id})
    except Exception as e:
        return Result.error(str(e))


def handle_execution_success(db_path_or_url, execution_id):
    try:
        return set_execution_status(db_path_or_url, execution_id, "completed")
    except Exception as e:
        return Result.error(str(e))


def handle_execution_failure(db_path_or_url, execution_id):
    try:
        return set_execution_status(db_path_or_url, execution_id, "failed")
    except Exception as e:
        return Result.error(str(e))


def complete_execution(db_path_or_url, execution_id):
    try:
        result = combine_execution_records_results(db_path_or_url, execution_id)
        if not result.success:
            return result
        return set_execution_result(db_path_or_url, execution_id, result.data)
    except Exception as e:
        return Result.error(str(e))


def finalize_execution(db_path_or_url, execution_id, status):
    try:
        status_result = set_execution_status(db_path_or_url, execution_id, status)
        result_result = complete_execution(db_path_or_url, execution_id)
        if not status_result.success:
            return status_result
        if not result_result.success:
            return result_result
        return Result.success({
            "finalized": True,
            "execution_id": execution_id,
            "status": status
        })
    except Exception as e:
        return Result.error(str(e))


def batch_update_dependencies(db_path_or_url, execution_id, updates):
    try:
        with DatabaseConnection(db_path_or_url) as session:
            updated = 0
            for node_id in updates:
                task = session.query(ExecutionQueue).filter_by(
                    execution_id=execution_id, node_id=node_id
                ).first()
                if task:
                    task.dependency_count = max(0, task.dependency_count - 1)
                    if task.dependency_count == 0 and task.status == "pending":
                        task.status = "ready"
                    updated += 1
            return Result.success({"updated_tasks": updated})
    except Exception as e:
        return Result.error(str(e))


def trigger_workflow_execution(db_path_or_url, workflow_id, initial_node_ids):
    try:
        result = create_execution(db_path_or_url, workflow_id)
        if not result.success:
            return result
        execution_id = result.data["execution_id"]

        created = []
        for node_id in initial_node_ids:
            task_result = create_task(db_path_or_url, execution_id, node_id, dependency_count=0)
            if not task_result.success:
                print(f"❌ Task oluşturulamadı: node_id={node_id}, hata={task_result.error}")
                return Result.error(f"Node {node_id} için task oluşturulamadı: {task_result.error}")
            created.append(task_result.data["queue_id"])

        return Result.success({
            "execution_id": execution_id,
            "created_tasks": len(created),
            "ready_tasks": len(created),
            "initial_tasks": created
        })
    except Exception as e:
        return Result.error(str(e))


def get_execution_status_summary(db_path_or_url, execution_id):
    try:
        with DatabaseConnection(db_path_or_url) as session:
            total = session.query(ExecutionQueue).filter_by(execution_id=execution_id).count()
            completed = session.query(ExecutionQueue).filter_by(
                execution_id=execution_id, status="completed").count()
            running = session.query(ExecutionQueue).filter_by(
                execution_id=execution_id, status="running").count()
            pending = session.query(ExecutionQueue).filter_by(
                execution_id=execution_id, status="pending").count()
            ready = session.query(ExecutionQueue).filter_by(
                execution_id=execution_id, status="ready").count()

            return Result.success({
                "execution_id": execution_id,
                "total": total,
                "completed": completed,
                "running": running,
                "pending": pending,
                "ready": ready
            })
    except Exception as e:
        return Result.error(str(e))


def create_workflow_with_components(db_path_or_url, workflow_name, nodes, edges):
    try:
        wf_result = create_workflow(db_path_or_url, name=workflow_name)
        if not wf_result.success:
            return wf_result
        workflow_id = wf_result.data["workflow_id"]

        node_id_map = {}
        for n in nodes:
            n_result = create_node(db_path_or_url, workflow_id, **n)
            if not n_result.success:
                return n_result
            node_id_map[n["name"]] = n_result.data["node_id"]

        for e in edges:
            from_id = node_id_map.get(e["from"])
            to_id = node_id_map.get(e["to"])
            if not from_id or not to_id:
                return Result.error(f"Invalid edge: {e}")
            edge_result = create_edge(
                db_path_or_url, workflow_id, from_id, to_id, e.get("condition_type", "success")
            )
            if not edge_result.success:
                return edge_result

        return Result.success({
            "workflow_id": workflow_id,
            "nodes_created": list(node_id_map.values()),
            "edges_created": len(edges)
        })
    except Exception as e:
        return Result.error(str(e))
