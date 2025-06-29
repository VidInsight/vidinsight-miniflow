from datetime import datetime
import json 
import uuid

def generate_uuid():
    return str(uuid.uuid4())

def generate_timestamp():
    return datetime.utcnow().isoformat() + "Z"

def safe_json_dumps(data):
    try:
        if data is None:
            return "{}"
        return json.dumps(data, ensure_ascii=False, separators=(',', ':'))
    except (TypeError, ValueError):
        return "{}"

def safe_json_loads(json_str):
    if not json_str or not isinstance(json_str, str):
        return {}
    
    try:
        return json.loads(json_str)
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}