# functions/execution_queue_table.py
from ..config import DatabaseConnection
from ..schema import ExecutionQueue, Execution, Node
from ..utils import generate_uuid
from ..exceptions import Result


def create_task(db_path_or_url, execution_id, node_id, dependency_count, priority=0):
    try:
        with DatabaseConnection(db_path_or_url) as session:
            task_id = generate_uuid()
            initial_status = "ready" if dependency_count == 0 else "pending"
            task = ExecutionQueue(
                id=task_id,
                execution_id=execution_id,
                node_id=node_id,
                status=initial_status,
                priority=priority,
                dependency_count=dependency_count
            )
            session.add(task)
            return Result.success({"queue_id": task_id})
    except Exception as e:
        return Result.error(str(e))


def get_task(db_path_or_url, task_id):
    try:
        with DatabaseConnection(db_path_or_url) as session:
            task = session.get(ExecutionQueue, task_id)
            if not task:
                return Result.success(None)
            return Result.success({
                "id": task.id,
                "execution_id": task.execution_id,
                "node_id": task.node_id,
                "status": task.status,
                "priority": task.priority,
                "dependency_count": task.dependency_count
            })
    except Exception as e:
        return Result.error(str(e))


def delete_task(db_path_or_url, task_id):
    try:
        with DatabaseConnection(db_path_or_url) as session:
            task = session.get(ExecutionQueue, task_id)
            if not task:
                return Result.error(f"Task not found: {task_id}")
            session.delete(task)
            return Result.success({"removed": True})
    except Exception as e:
        return Result.error(str(e))


def list_tasks(db_path_or_url, status=None):
    try:
        with DatabaseConnection(db_path_or_url) as session:
            query = session.query(ExecutionQueue).join(Node)
            if status:
                query = query.filter(ExecutionQueue.status == status)
            query = query.order_by(ExecutionQueue.priority.desc(), ExecutionQueue.dependency_count.asc())

            tasks = query.all()
            result = [{
                "id": t.id,
                "execution_id": t.execution_id,
                "node_id": t.node_id,
                "status": t.status,
                "priority": t.priority,
                "dependency_count": t.dependency_count,
                "node_name": t.node.name,
                "node_type": t.node.type
            } for t in tasks]
            return Result.success(result)
    except Exception as e:
        return Result.error(str(e))


def count_tasks(db_path_or_url, execution_id, status=None):
    try:
        with DatabaseConnection(db_path_or_url) as session:
            query = session.query(ExecutionQueue).filter(ExecutionQueue.execution_id == execution_id)
            if status:
                query = query.filter(ExecutionQueue.status == status)
            return Result.success(query.count())
    except Exception as e:
        return Result.error(str(e))


def list_execution_tasks(db_path_or_url, execution_id, status=None):
    try:
        with DatabaseConnection(db_path_or_url) as session:
            query = session.query(ExecutionQueue).join(Node).filter(ExecutionQueue.execution_id == execution_id)
            if status:
                query = query.filter(ExecutionQueue.status == status)
            query = query.order_by(ExecutionQueue.priority.desc(), ExecutionQueue.dependency_count.asc())

            tasks = query.all()
            result = [{
                "id": t.id,
                "status": t.status,
                "priority": t.priority,
                "dependency_count": t.dependency_count,
                "node_name": t.node.name,
                "node_type": t.node.type,
                "script": t.node.script,
                "params": t.node.params
            } for t in tasks]
            return Result.success(result)
    except Exception as e:
        return Result.error(str(e))


def delete_execution_tasks(db_path_or_url, execution_id):
    try:
        with DatabaseConnection(db_path_or_url) as session:
            cancelled = session.query(ExecutionQueue).filter(
                ExecutionQueue.execution_id == execution_id,
                ExecutionQueue.status.notin_(["running", "completed"])
            ).all()
            for task in cancelled:
                task.status = "cancelled"

            deleted = session.query(ExecutionQueue).filter(
                ExecutionQueue.execution_id == execution_id,
                ExecutionQueue.status == "cancelled"
            ).delete()
            return Result.success({
                "cancelled_tasks": len(cancelled),
                "deleted_tasks": deleted
            })
    except Exception as e:
        return Result.error(str(e))


def find_in_queue(db_path_or_url, execution_id, node_id):
    try:
        with DatabaseConnection(db_path_or_url) as session:
            task = session.query(ExecutionQueue).filter_by(
                execution_id=execution_id,
                node_id=node_id
            ).first()
            return Result.success({
                "id": task.id,
                "status": task.status,
                "priority": task.priority,
                "dependency_count": task.dependency_count
            } if task else None)
    except Exception as e:
        return Result.error(str(e))


def reorder_execution_queue(db_path_or_url):
    try:
        with DatabaseConnection(db_path_or_url) as session:
            updated_count = session.query(ExecutionQueue).filter(
                ExecutionQueue.dependency_count == 0,
                ExecutionQueue.status == "pending"
            ).update({ExecutionQueue.status: "ready"}, synchronize_session=False)

            ready_tasks = session.query(ExecutionQueue).join(Node).filter(
                ExecutionQueue.status == "ready"
            ).order_by(ExecutionQueue.priority.desc(), ExecutionQueue.dependency_count.asc()).all()

            result = [{
                "id": t.id,
                "execution_id": t.execution_id,
                "node_id": t.node_id,
                "node_name": t.node.name,
                "node_type": t.node.type,
                "status": t.status,
                "priority": t.priority,
                "dependency_count": t.dependency_count
            } for t in ready_tasks]
            return Result.success({
                "ready_tasks_updated": updated_count,
                "ready_tasks": result,
                "ready_count": len(result)
            })
    except Exception as e:
        return Result.error(str(e))


def decrease_dependency_count(db_path_or_url, task_id):
    try:
        with DatabaseConnection(db_path_or_url) as session:
            task = session.get(ExecutionQueue, task_id)
            if not task:
                return Result.error(f"Task not found: {task_id}")

            old_count = task.dependency_count
            task.dependency_count = max(0, task.dependency_count - 1)

            if task.dependency_count == 0 and task.status == "pending":
                task.status = "ready"

            return Result.success({
                "task_id": task.id,
                "old_dependency_count": old_count,
                "new_dependency_count": task.dependency_count,
                "new_status": task.status
            })
    except Exception as e:
        return Result.error(str(e))


def update_task_status(db_path_or_url, task_id, new_status):
    try:
        with DatabaseConnection(db_path_or_url) as session:
            task = session.get(ExecutionQueue, task_id)
            if not task:
                return Result.error(f"Task not found: {task_id}")
            task.status = new_status
            return Result.success({
                "updated": True,
                "task_id": task_id,
                "new_status": new_status
            })
    except Exception as e:
        return Result.error(str(e))
