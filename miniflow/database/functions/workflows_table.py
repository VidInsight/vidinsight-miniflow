# functions/workflows_table.py
from ..config import DatabaseConnection
from ..schema import Workflow
from ..utils import generate_uuid, generate_timestamp
from ..exceptions import Result


def create_workflow(db_path_or_url, name, description=None, status="active", version=1, created_at=None, updated_at=None):
    try:
        from datetime import datetime
        with DatabaseConnection(db_path_or_url) as session:
            workflow_id = generate_uuid()
            created_at = created_at or datetime.utcnow()
            updated_at = updated_at or datetime.utcnow()

            workflow = Workflow(
                id=workflow_id,
                name=name,
                description=description,
                status=status,
                version=version,
                created_at=created_at,
                updated_at=updated_at
            )

            session.add(workflow)
            return Result.success({"workflow_id": workflow_id})

    except Exception as e:
        return Result.error(str(e))


def get_workflow(db_path_or_url, workflow_id):
    try:
        with DatabaseConnection(db_path_or_url) as session:
            workflow = session.get(Workflow, workflow_id)
            if workflow:
                return Result.success({
                    "id": workflow.id,
                    "name": workflow.name,
                    "description": workflow.description,
                    "status": workflow.status,
                    "version": workflow.version,
                    "created_at": workflow.created_at.isoformat(),
                    "updated_at": workflow.updated_at.isoformat()
                })
            else:
                return Result.success(None)
    except Exception as e:
        return Result.error(str(e))


def list_workflows(db_path_or_url, limit=100, offset=0):
    try:
        with DatabaseConnection(db_path_or_url) as session:
            workflows = (
                session.query(Workflow)
                .order_by(Workflow.created_at.desc())
                .offset(offset)
                .limit(limit)
                .all()
            )
            result = [
                {
                    "id": w.id,
                    "name": w.name,
                    "description": w.description,
                    "status": w.status,
                    "version": w.version,
                    "created_at": w.created_at.isoformat(),
                    "updated_at": w.updated_at.isoformat()
                } for w in workflows
            ]
            return Result.success(result)
    except Exception as e:
        return Result.error(str(e))


def delete_workflow(db_path_or_url, workflow_id):
    try:
        with DatabaseConnection(db_path_or_url) as session:
            workflow = session.get(Workflow, workflow_id)
            if not workflow:
                return Result.error(f"Workflow not found: {workflow_id}")
            session.delete(workflow)
            return Result.success({"deleted": True, "workflow_id": workflow_id})
    except Exception as e:
        return Result.error(str(e))
