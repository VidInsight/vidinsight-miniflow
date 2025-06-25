# functions/nodes_table.py
from sqlalchemy.orm import joinedload
from ..config import DatabaseConnection
from ..schema import Node, Workflow
from ..utils import generate_uuid, safe_json_dumps, safe_json_loads
from ..exceptions import Result


def create_node(db_path_or_url, workflow_id, name, type, script=None, params=None):
    try:
        with DatabaseConnection(db_path_or_url) as session:
            workflow = session.get(Workflow, workflow_id)
            if not workflow:
                return Result.error(f"Workflow not found: {workflow_id}")

            node_id = generate_uuid()
            node = Node(
                id=node_id,
                workflow_id=workflow_id,
                name=name,
                type=type,
                script=script,
                params=safe_json_dumps(params)
            )
            session.add(node)
            return Result.success({"node_id": node_id})
    except Exception as e:
        return Result.error(str(e))


def get_node(db_path_or_url, node_id):
    try:
        with DatabaseConnection(db_path_or_url) as session:
            node = session.get(Node, node_id)
            if node:
                return Result.success({
                    "id": node.id,
                    "workflow_id": node.workflow_id,
                    "name": node.name,
                    "type": node.type,
                    "script": node.script,
                    "params": safe_json_loads(node.params)
                })
            return Result.success(None)
    except Exception as e:
        return Result.error(str(e))


def list_nodes(db_path_or_url):
    try:
        with DatabaseConnection(db_path_or_url) as session:
            nodes = session.query(Node).all()
            result = [{
                "id": node.id,
                "workflow_id": node.workflow_id,
                "name": node.name,
                "type": node.type,
                "script": node.script,
                "params": safe_json_loads(node.params)
            } for node in nodes]
            return Result.success(result)
    except Exception as e:
        return Result.error(str(e))


def list_workflow_nodes(db_path_or_url, workflow_id):
    try:
        with DatabaseConnection(db_path_or_url) as session:
            nodes = session.query(Node).filter_by(workflow_id=workflow_id).all()
            result = [{
                "id": node.id,
                "name": node.name,
                "type": node.type,
                "script": node.script,
                "params": safe_json_loads(node.params)
            } for node in nodes]
            return Result.success(result)
    except Exception as e:
        return Result.error(str(e))


def delete_node(db_path_or_url, node_id):
    try:
        with DatabaseConnection(db_path_or_url) as session:
            node = session.get(Node, node_id)
            if not node:
                return Result.error(f"Node not found: {node_id}")
            session.delete(node)
            return Result.success({"deleted": True, "node_id": node_id})
    except Exception as e:
        return Result.error(str(e))


def delete_workflow_nodes(db_path_or_url, workflow_id):
    try:
        with DatabaseConnection(db_path_or_url) as session:
            nodes = session.query(Node).filter_by(workflow_id=workflow_id).all()
            count = len(nodes)
            for node in nodes:
                session.delete(node)
            return Result.success({"deleted": count})
    except Exception as e:
        return Result.error(str(e))


def get_node_dependencies(db_path_or_url, node_id):
    try:
        with DatabaseConnection(db_path_or_url) as session:
            node = session.query(Node).options(joinedload(Node.to_edges)).filter_by(id=node_id).first()
            if not node:
                return Result.error(f"Node not found: {node_id}")
            dependencies = [edge.from_node_id for edge in node.to_edges]
            return Result.success(dependencies)
    except Exception as e:
        return Result.error(str(e))


def get_node_dependents(db_path_or_url, node_id):
    try:
        with DatabaseConnection(db_path_or_url) as session:
            node = session.query(Node).options(joinedload(Node.from_edges)).filter_by(id=node_id).first()
            if not node:
                return Result.error(f"Node not found: {node_id}")
            dependents = [edge.to_node_id for edge in node.from_edges]
            return Result.success(dependents)
    except Exception as e:
        return Result.error(str(e))


def update_node_params(db_path_or_url, node_id, new_params):
    try:
        with DatabaseConnection(db_path_or_url) as session:
            node = session.get(Node, node_id)
            if not node:
                return Result.error(f"Node not found: {node_id}")
            node.params = safe_json_dumps(new_params)
            return Result.success({"updated": True})
    except Exception as e:
        return Result.error(str(e))
