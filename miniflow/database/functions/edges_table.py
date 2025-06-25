# functions/edges_table.py
from sqlalchemy import text  # 🔸 PostgreSQL için raw SQL uyumluluğu (gerekirse)
from ..config import DatabaseConnection
from ..schema import Workflow, Edge, Node
from ..exceptions import Result
from ..utils import generate_uuid


def _nodes_same_workflow(session, from_node_id, to_node_id):
    from_node = session.get(Node, from_node_id)
    to_node = session.get(Node, to_node_id)

    if not from_node:
        return False, "From node not found"
    if not to_node:
        return False, "To node not found"
    if from_node.workflow_id != to_node.workflow_id:
        return False, f"Nodes belong to different workflows: {from_node.workflow_id} vs {to_node.workflow_id}"
    return True, from_node.workflow_id


def _edge_would_create_cycle(session, from_node_id, to_node_id):
    def dfs(current, target, visited):
        if current in visited:
            return False
        visited.add(current)
        if current == target:
            return True
        next_nodes = session.query(Edge.to_node_id).filter(Edge.from_node_id == current).all()
        return any(dfs(n.to_node_id, target, visited.copy()) for n in next_nodes)

    return dfs(to_node_id, from_node_id, set())


def create_edge(db_path_or_url, workflow_id, from_node_id, to_node_id, condition_type="success"):
    try:
        with DatabaseConnection(db_path_or_url) as session:
            if not session.get(Workflow, workflow_id):
                return Result.error(f"Workflow not found: {workflow_id}")

            is_valid, wf_or_error = _nodes_same_workflow(session, from_node_id, to_node_id)
            if not is_valid:
                return Result.error(wf_or_error)
            if wf_or_error != workflow_id:
                return Result.error("Nodes do not belong to the specified workflow")

            if from_node_id == to_node_id:
                return Result.error("Cannot create edge from node to itself")

            exists = session.query(Edge).filter_by(
                workflow_id=workflow_id,
                from_node_id=from_node_id,
                to_node_id=to_node_id,
                condition_type=condition_type
            ).first()
            if exists:
                return Result.error("Edge already exists with this condition type")

            if _edge_would_create_cycle(session, from_node_id, to_node_id):
                return Result.error("Cannot create edge: would create a cycle")

            edge = Edge(
                id=generate_uuid(),
                workflow_id=workflow_id,
                from_node_id=from_node_id,
                to_node_id=to_node_id,
                condition_type=condition_type
            )
            session.add(edge)
            return Result.success({"edge_id": edge.id})
    except Exception as e:
        return Result.error(str(e))


def get_edge(db_path_or_url, edge_id):
    try:
        with DatabaseConnection(db_path_or_url) as session:
            edge = session.get(Edge, edge_id)
            if not edge:
                return Result.success(None)
            return Result.success({
                "id": edge.id,
                "workflow_id": edge.workflow_id,
                "from_node_id": edge.from_node_id,
                "to_node_id": edge.to_node_id,
                "condition_type": edge.condition_type
            })
    except Exception as e:
        return Result.error(str(e))


def delete_edge(db_path_or_url, edge_id):
    try:
        with DatabaseConnection(db_path_or_url) as session:
            edge = session.get(Edge, edge_id)
            if not edge:
                return Result.error(f"Edge not found: {edge_id}")
            session.delete(edge)
            return Result.success({"deleted": True, "edge_id": edge_id})
    except Exception as e:
        return Result.error(str(e))


def list_edges(db_path_or_url):
    try:
        with DatabaseConnection(db_path_or_url) as session:
            edges = session.query(Edge).all()
            result = [{

                "id": e.id,
                "workflow_id": e.workflow_id,
                "from_node_id": e.from_node_id,
                "to_node_id": e.to_node_id,
                "condition_type": e.condition_type
            } for e in edges]
            return Result.success(result)
    except Exception as e:
        return Result.error(str(e))


def list_workflow_edges(db_path_or_url, workflow_id):
    try:
        with DatabaseConnection(db_path_or_url) as session:
            if not session.get(Workflow, workflow_id):
                return Result.error(f"Workflow not found: {workflow_id}")
            edges = session.query(Edge).filter_by(workflow_id=workflow_id).all()
            result = [{
                "id": e.id,
                "from_node_id": e.from_node_id,
                "to_node_id": e.to_node_id,
                "condition_type": e.condition_type
            } for e in edges]
            return Result.success(result)
    except Exception as e:
        return Result.error(str(e))


def delete_workflow_edges(db_path_or_url, workflow_id):
    try:
        with DatabaseConnection(db_path_or_url) as session:
            if not session.get(Workflow, workflow_id):
                return Result.error(f"Workflow not found: {workflow_id}")
            count = session.query(Edge).filter_by(workflow_id=workflow_id).delete()
            return Result.success({"deleted_count": count})
    except Exception as e:
        return Result.error(str(e))
