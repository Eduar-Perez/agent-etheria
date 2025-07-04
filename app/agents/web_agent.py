from textwrap import dedent
from typing import Optional

from agno.agent import Agent
from agno.models.aws import Claude
from agno.tools.duckduckgo import DuckDuckGoTools
from utilities.get_prompts import open_prompt


def get_web_agent_simple(
    model_id: str = "gpt-4.1",
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    debug_mode: bool = True,
    instruction_user: Optional[str] = None,
    description_user: Optional[str] = None,
    tools_input: Optional[bool] = None,
) -> Agent:

    instructions_hardcode = open_prompt("./agents/prompts/web_agent.txt")
    instructions_hardcode = instructions_hardcode.format(current_user_id=user_id)
    instructions_end = (
        dedent(instruction_user) if instruction_user else instructions_hardcode
    )
    descriptions_hardcode = open_prompt("./agents/prompts/web_agent_description.txt")
    description_end = (
        dedent(description_user) if description_user else descriptions_hardcode
    )
    tools = [DuckDuckGoTools()] if tools_input else []
    return Agent(
        name="Web Search Agent",
        agent_id="web_search_agent",
        user_id=user_id,
        session_id=session_id,
        model=Claude(id=model_id),
        tools=tools,
        description=description_end,
        instructions=instructions_end,
        add_state_in_messages=True,
        # **Sin storage ni historial**
        storage=None,
        add_history_to_messages=False,
        read_chat_history=False,
        enable_agentic_memory=False,
        markdown=True,
        add_datetime_to_instructions=True,
        debug_mode=debug_mode,
    )
