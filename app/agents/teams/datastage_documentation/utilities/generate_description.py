import os
import re
import json
import logging
from agents import AgentType
from agents.agent_selector import get_agent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def open_prompt(full_path: str) -> str:
    with open(full_path, "r", encoding="utf-8") as file:
        return file.read()
    
def descripcion_generador(descripcion):
    agent_enum = AgentType.DESCRIPTION_AGENT
    prompt_template = open_prompt("agents/prompts/descripcion_por_jobs_prompt.txt")
    prompt = prompt_template.format(
    jobs_json=json.dumps(descripcion, ensure_ascii=False, indent=2)
)
    agent = get_agent(
        model="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
        agent_id=agent_enum,
        user_id="user_id",
        session_id="session_id"
        )
    descripcion = agent.run(prompt)
    raw = descripcion.content.strip()

    # Limpiar etiquetas Markdown
    raw = re.sub(r'^```json\s*', '', raw)
    raw = re.sub(r'\s*```$', '', raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        logger.error("Error al parsear JSON desde el modelo Claude: %s", e)
        logger.error("Contenido recibido:\n%s", raw)
        raise