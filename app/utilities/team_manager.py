import base64
import os
import uuid
from agents.teams import join_sql_scripts_team


def team_manager(request):
    if request.agent_id == "team_join_sql":
        UPLOAD_DIR = "./tmp/sql_inputs"
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        saved_paths = []
        for file_item in request.files:
            content = base64.b64decode(file_item.file)
            unique_filename = f"{file_item.fileName}"
            file_path = os.path.join(UPLOAD_DIR, unique_filename)
            with open(file_path, "wb") as f:
                f.write(content)
            saved_paths.append(file_path)
        return join_sql_scripts_team(UPLOAD_DIR)
    else:
        raise ValueError(f"Invalid agent ID: {request.agent_id}")
