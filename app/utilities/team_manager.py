import base64
import os
import uuid
from agents.teams import join_sql_scripts_team, odi_migration_team

from typing import List

def save_base64_files(file_items: List[dict], upload_dir: str) -> List[str]:
    os.makedirs(upload_dir, exist_ok=True)
    for item in file_items:
        print(item.file)
        file_content = base64.b64decode(item.file)
        filename = item.fileName
        file_path = os.path.join(upload_dir, filename)
        with open(file_path, "wb") as f:
            f.write(file_content)


def team_manager(request):
    team_id = request.agent_id
    
    if team_id == "team_join_sql":
        # upload_dir = "./tmp/sql_inputs"
        # save_base64_files(request.files, upload_dir)
        # return join_sql_scripts_team(upload_dir)
        return "team_join_sql"
    
    elif team_id == "team_odi_migration":
        upload_dir = os.path.join(os.path.dirname(__file__), "..", "..", "tmp", "odi_inputs")
        save_base64_files(request.files, upload_dir)
        return odi_migration_team(upload_dir)
    else:
        raise ValueError(f"Invalid agent ID: {request.agent_id}")
