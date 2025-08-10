import os
import re

def create_script(scripts_dir: str, script_name:str, script_extension: str, script_content: str):
    # Script dosyasını script_name ile scripts klasörüne kaydet
    script_filename = f"{script_name}.{script_extension}"
    script_file_path = scripts_dir / script_filename

    # File content'i dosyaya yaz
    with open(script_file_path, 'w', encoding='utf-8') as target_file:
        target_file.write(script_content)

    # Absolute path'i hesapla
    absolute_path = str(script_file_path.resolve())

    return absolute_path

def delete_script(scripts_dir: str, script_name: str):
    """Delete a script file from the scripts directory"""
    script_filename = f"{script_name}.py"
    script_file_path = scripts_dir / script_filename
    
    if script_file_path.exists():
        script_file_path.unlink()  # Delete the file
        print(f"Script file deleted: {script_file_path}")
        return True
    else:
        print(f"Script file does not exist: {script_file_path}")
        return False

def extract_dynamic_node_params(node_params):
    pattern = r"\{\{(.*?)\}\}"
    dynamic_params = {}

    for key, value in node_params.items():
        if isinstance(value, str):
            match = re.search(pattern, value)
            if match:
                content = match.group(1).strip()
                # Skip environment variables (those starting with $)
                if not content.startswith('$'):
                    dynamic_params[key] = content
    return dynamic_params

def extract_env_var_params(node_params):
    """
    Extract environment variable references from node parameters
    Supports formats: 
    - {{env:variable_name}} (new preferred format)
    - {{$variable_name}} (legacy format)
    Returns dict of param_key -> env_var_name mappings
    """
    env_params = {}

    for key, value in node_params.items():
        if isinstance(value, str):
            # Try new format first: {{env:variable_name}}
            pattern_new = r"\{\{env:([A-Za-z_][A-Za-z0-9_]*)\}\}"
            match = re.search(pattern_new, value)
            if match:
                env_params[key] = match.group(1).strip()
                continue
                
            # Fallback to legacy format: {{$variable_name}}
            pattern_legacy = r"\{\{\$([A-Za-z_][A-Za-z0-9_]*)\}\}"
            match = re.search(pattern_legacy, value)
            if match:
                env_params[key] = match.group(1).strip()
    return env_params

def split_variable_reference(variable_reference):
    variable_parts = variable_reference.strip().split('.')
    if len(variable_parts) == 2:
        return variable_parts[0], variable_parts[1]
    
    raise ValueError(f"Invalid variable reference: {variable_reference}")
    
