import logging
from agents import AgentType
from agents.agent_selector import get_agent
from .get_prompts import open_prompt

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def intro_generator(json_info):
    prompt_template = open_prompt("agents/prompts/intro_datastage_prompt.txt")
    prompt = prompt_template.format(input_json=json_info)
    agent_enum = AgentType.INTRO
    agent = get_agent(
        model="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
        agent_id=agent_enum,
        user_id="user_id",
        session_id="session_id"
        )
    intro = agent.run(prompt)
    return intro.content.strip()