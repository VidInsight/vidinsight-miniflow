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
    if os.path.exists("demofile.txt"):
        os.remove("demofile.txt")
    else:
        print("The file does not exist")

def extract_dynamic_node_params(node_params):
    pattern = r"\{\{(.*?)\}\}"
    extract_dynamic_node_params = {}

    for key, value in node_params.items():
        if isinstance(value, str):
            match = re.search(pattern, value)
            if match:
                extract_dynamic_node_params[key] = match.group(1).strip()
    return extract_dynamic_node_params

def split_variable_refrence(variable_refrence):
    variable_parts = variable_refrence.strip().split('.')
    if len(variable_parts) == 2:
        variable_parts[0], variable_parts[1]
    
    raise ValueError(f"Invalid variable reference: {variable_refrence}")
    
