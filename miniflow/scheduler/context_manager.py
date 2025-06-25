import re
import json

from ..database.exceptions import Result
from ..database.config import DatabaseConnection
from ..database.schema import Execution, Node, ExecutionResult


def extract_dynamic_values(params):
    pattern = r"\{\{(.*?)\}\}"
    extracted = {}

    for key, value in params.items():
        if isinstance(value, str):
            match = re.search(pattern, value)
            if match:
                extracted[key] = match.group(1).strip()

    return extracted


def split_variable_path(path: str):
    parts = path.strip().split('.', 1)
    return (parts[0], parts[1]) if len(parts) == 2 else (parts[0], None)


def find_node_id(db_path, execution_id, node_name):
    """
    execution_id ile ilişkili workflow_id'yi bul, ardından node_name'e sahip node'un ID'sini al.
    """
    try:
        with DatabaseConnection(db_path) as session:
            execution = session.query(Execution).get(execution_id)
            if not execution or execution.status == "failed":
                return None

            workflow_id = execution.workflow_id

            node = session.query(Node).filter_by(workflow_id=workflow_id, name=node_name).first()
            return node.id if node else None
    except Exception as e:
        print(f"[DEBUG] find_node_id hatası: {e}")
        return None


def get_result_data_for_node(db_path, execution_id, node_id):
    """
    execution_id + node_id için result_data'yı döner.
    """
    try:
        with DatabaseConnection(db_path) as session:
            result = session.query(ExecutionResult).filter_by(
                execution_id=execution_id,
                node_id=node_id
            ).first()

            if not result:
                return {}

            if result.status != "success":
                return {"error": result.error_message or "Execution failed"}

            if result.result_data:
                try:
                    return json.loads(result.result_data)
                except json.JSONDecodeError:
                    return {"error": "Invalid JSON"}

            return {}

    except Exception as e:
        print(f"[DEBUG] get_result_data_for_node hatası: {e}")
        return {}


def create_context(params_dict, execution_id, db_path):
    """
    Parametrelerdeki {{dynamic}} değişkenlerini çözümleyip yerine değerlerini koyar.
    """
    dynamic_values = extract_dynamic_values(params_dict)

    for param_name, path in dynamic_values.items():
        node_name, attribute = split_variable_path(path)
        node_id = find_node_id(db_path, execution_id, node_name)

        if node_id:
            result_data = get_result_data_for_node(db_path, execution_id, node_id)

            if result_data and isinstance(result_data, dict):
                value = result_data.get(attribute)
                if value is not None:
                    params_dict[param_name] = value

    return params_dict


def create_context_for_task(params_dict, execution_id, db_path):
    """
    JSON string veya dict olarak gelen params_dict'i işler, dynamic value'ları çözümler.
    """
    try:
        if isinstance(params_dict, dict):
            params = params_dict
        else:
            try:
                params = json.loads(params_dict)
            except json.JSONDecodeError:
                return {}

        return create_context(params, execution_id, db_path)

    except Exception as e:
        print(f"[DEBUG] create_context_for_task hatası: {e}")
        return {}
