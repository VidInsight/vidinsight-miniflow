import os

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