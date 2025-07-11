from textwrap import dedent
from typing import Optional
from agno.models.aws import Claude
from agno.agent import Agent
from agno.tools.duckduckgo import DuckDuckGoTools
from utilities.get_prompts import open_prompt


def get_claud_agent(
   model_id: str = "claude-3-sonnet-20240229",
   user_id: Optional[str] = None,
   session_id: Optional[str] = None,
   debug_mode: bool = False,
   instruction_user: Optional[str] = None,
   description_user: Optional[str] = None,
   tools_input: Optional[bool] = None
) -> Agent:
   instructions_hardcode = open_prompt("./agents/prompts/claude_agent.txt")
   instructions_end = (
        dedent(instruction_user) if instruction_user else instructions_hardcode
    )
    descriptions_hardcode = open_prompt("./agents/prompts/claude_agent_description.txt")
    description_end = (
        dedent(description_user) if description_user else descriptions_hardcode
    )
   description_end = dedent(description_user) if description_user else descriptions_hardcode
   return Agent(
      name="Claud Agent",
      agent_id="claud_agent",
      user_id=user_id,
      session_id=session_id,
      model=Claude(id=model_id),
      tools=[DuckDuckGoTools()],
      description=description_end,
      instructions=instructions_end,
      storage=None,
      add_history_to_messages=False,
      read_chat_history=False,
      enable_agentic_memory=False,
      markdown=True,
      add_datetime_to_instructions=True,
      debug_mode=debug_mode,
   )
