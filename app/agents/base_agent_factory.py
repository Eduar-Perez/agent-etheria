from typing import Optional, List
from textwrap import dedent
from agno.agent import Agent
from agno.models.aws import Claude
from utilities.get_prompts import open_prompt
from agno.tools.duckduckgo import DuckDuckGoTools

class BaseAgentFactory:
    def __init__(
        self,
        agent_id: str,
        name: str,
        prompt_file: str,
        description_file: str,
        default_model: str = "gpt-4.1",
        extra_tools: Optional[List] = None,
        memory_enabled: bool = False,
        state_enabled: bool = False,
    ):
        self.agent_id = agent_id
        self.name = name
        self.prompt_file = prompt_file
        self.description_file = description_file
        self.default_model = default_model
        self.extra_tools = extra_tools or []
        self.memory_enabled = memory_enabled
        self.state_enabled = state_enabled

    def build(
        self,
        model_id: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        debug_mode: bool = False,
        instruction_user: Optional[str] = None,
        description_user: Optional[str] = None,
        tools_input: Optional[bool] = None,
    ) -> Agent:
        prompt_text = open_prompt(self.prompt_file).format(current_user_id=user_id)
        instructions = dedent(instruction_user) if instruction_user else prompt_text

        description_text = open_prompt(self.description_file)
        description = dedent(description_user) if description_user else description_text

        tools = [DuckDuckGoTools()] if tools_input else []
        tools += self.extra_tools

        return Agent(
            name=self.name,
            agent_id=self.agent_id,
            user_id=user_id,
            session_id=session_id,
            model=Claude(id=model_id or self.default_model),
            tools=tools,
            instructions=instructions,
            description=description,
            storage=None,
            add_state_in_messages=self.state_enabled,
            add_history_to_messages=False,
            read_chat_history=False,
            enable_agentic_memory=self.memory_enabled,
            markdown=True,
            add_datetime_to_instructions=True,
            debug_mode=debug_mode,
        )
