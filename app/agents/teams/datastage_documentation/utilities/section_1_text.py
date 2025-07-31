import os
import json
import logging
from agents import AgentType
from agents.agent_selector import get_agent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def open_prompt(full_path: str) -> str:
    with open(full_path, "r", encoding="utf-8") as file:
        return file.read()
    
def intro_section_1(json_info):
    agent_enum = AgentType.SECTION_1_AGENT
    prompt_template = open_prompt("agents/prompts/section_1_input.txt")
    json_str = json.dumps(json_info, ensure_ascii=False, indent=2)
    prompt = prompt_template.format(json_info=json_str)
    agent = get_agent(
        model="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
        agent_id=agent_enum,
        user_id="user_id",
        session_id="session_id"
        )
    section_1 = agent.run(prompt)
    return section_1.content.strip()