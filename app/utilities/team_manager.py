import os
import uuid
import shutil
import base64
from typing import List
from agents.teams import join_sql_scripts_team, odi_migration_team,bus_migration_team, generate_document_datastage
def eliminar_carpeta_completa(path: str):
    if os.path.exists(path) and os.path.isdir(path):
        shutil.rmtree(path)
        print(f"Carpeta eliminada: {path}")
    else:
        print(f"La ruta no existe o no es una carpeta: {path}")

def save_base64_files(file_items: List[dict], upload_dir: str) -> List[str]:
    os.makedirs(upload_dir, exist_ok=True)
    if len(file_items) < 1:
        return "No se recibieron los archivos para procesar"
    for item in file_items:
        file_content = base64.b64decode(item.file.split(",")[1])
        filename = item.fileName
        file_path = os.path.join(upload_dir, filename)
        with open(file_path, "wb") as f:
            f.write(file_content)

def team_manager(request):
    team_id = request.agent_id
    if team_id == "team_join_sql":
        if len(request.files) < 1:
            return "Para hacer este procesamiento, necesito que cargues los archivos de sql que deseas unificar"
        upload_dir = os.path.join(os.path.dirname(__file__), "..", "..", "tmp", "sql_inputs")
        save_base64_files(request.files, upload_dir)
        response = join_sql_scripts_team(upload_dir)
        eliminar_carpeta_completa(upload_dir)
        return response
    
    elif team_id == "team_odi_migration":
        if len(request.files) < 1:
            return "Para hacer la migración a datastage se necesita que se cargue el archivo .XML que deseas migrar"
        upload_dir = os.path.join(os.path.dirname(__file__), "..", "..", "tmp", "odi_inputs")
        save_base64_files(request.files, upload_dir)
        response = odi_migration_team(upload_dir)
        eliminar_carpeta_completa(upload_dir)
        print("Response from ODI migration team:", response)
        return response
    
    elif team_id == "team_bus_migration":
        if len(request.files) < 1:
            return "Para hacer este procesamiento, necesito que cargues los archivos de esq y excel"
        upload_dir = os.path.join(os.path.dirname(__file__), "..", "..", "tmp", "bus_migration_inputs")
        save_base64_files(request.files, upload_dir)
        response = bus_migration_team(upload_dir)
        eliminar_carpeta_completa(upload_dir)
        return response
    elif team_id == "team_datastage_documentation": 
        if len(request.files) < 1:
            return "Para hacer este procesamiento, necesito que cargues los archivos de esq y excel"
        upload_dir = os.path.join(os.path.dirname(__file__), "..", "..", "tmp", "datastage_documentation_input")
        save_base64_files(request.files, upload_dir)
        response = generate_document_datastage(upload_dir)
        eliminar_carpeta_completa(upload_dir)
        return response
    else:
        raise ValueError(f"Invalid agent ID: {request.agent_id}")
