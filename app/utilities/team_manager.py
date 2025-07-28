import base64
import os
import uuid
from agents.teams import join_sql_scripts_team, odi_migration_team,bus_migration_team

from typing import List

def save_base64_files(file_items: List[dict], upload_dir: str) -> List[str]:
    os.makedirs(upload_dir, exist_ok=True)
    if len(file_items) < 1:
        return "No se encontraron archivos en la carpeta proporcionada"
    for item in file_items:
        file_content = base64.b64decode(item.file)
        filename = item.fileName
        file_path = os.path.join(upload_dir, filename)
        with open(file_path, "wb") as f:
            f.write(file_content)

def team_manager(request):
    team_id = request.agent_id
    if team_id == "team_join_sql":
        if len(request.files) < 1:
            return "Para hacer este procesamiento, necesito que cargues los archivos de sql que deseas unificar"
        upload_dir = "./tmp/sql_inputs"
        save_base64_files(request.files, upload_dir)
        return join_sql_scripts_team(upload_dir)
    elif team_id == "team_odi_migration":
        if len(request.files) < 1:
            return "Para hacer la migración a datastage se necesita que se cargue el archivo .XML que deseas migrar"
        upload_dir = os.path.join(os.path.dirname(__file__), "..", "..", "tmp", "odi_inputs")
        save_base64_files(request.files, upload_dir)
        response = odi_migration_team(upload_dir)
        print("Response from ODI migration team:", response)
        return response
    elif team_id == "team_bus_migration":
        if len(request.files) < 1:
            return "Para hacer este procesamiento, necesito que cargues los archivos de esq y excel"
        upload_dir = os.path.join(os.path.dirname(__file__), "..", "..", "tmp", "bus_migration_inputs")
        save_base64_files(request.files, upload_dir)
        response = bus_migration_team(input_files=upload_dir)
        
    else:
        raise ValueError(f"Invalid agent ID: {request.agent_id}")
