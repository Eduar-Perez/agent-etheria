from typing import Optional, Union
from .agent_type import AgentType
from .factory import AGENTS

def get_agent(
    model: str = "gpt-4.1",
    agent_id: Optional[Union[AgentType, str]] = None,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    debug_mode: bool = True,
    instruction_user: Optional[str] = None,
    description_user: Optional[str] = None,
    tools_input: Optional[bool] = None,
):
    if agent_id is None:
        raise ValueError("Agent ID must be provided")

    # Si el agent_id viene como string, conviértelo a Enum
    if isinstance(agent_id, str):
        try:
            agent_id = AgentType(agent_id)
        except ValueError:
            raise ValueError(f"Unknown agent ID: {agent_id}")

    factory = AGENTS.get(agent_id.value)
    if not factory:
        raise ValueError(f"Agent '{agent_id.value}' not found")

    return factory.build(
        model_id=model,
        user_id=user_id,
        session_id=session_id,
        debug_mode=debug_mode,
        instruction_user=instruction_user,
        description_user=description_user,
        tools_input=tools_input,
    )
