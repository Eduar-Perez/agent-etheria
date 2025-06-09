from typing import Optional, Union
from agent_type import AgentType
from web_agent import get_web_agent_simple
from agno_assist import get_agno_assist_simple
from finance_agent import get_finance_agent

def get_agent(
    model_id: str = "gpt-4.1",
    agent_id: Optional[Union[AgentType, str]] = None,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    debug_mode: bool = True,
):
    if agent_id is None:
        raise ValueError("Agent ID must be provided")

    if isinstance(agent_id, str):
        try:
            agent_id = AgentType(agent_id)
        except ValueError:
            raise ValueError(f"Unknown agent ID: {agent_id}")

    if agent_id == AgentType.WEB_AGENT:
        return get_web_agent_simple(
            model_id=model_id,
            user_id=user_id,
            session_id=session_id,
            debug_mode=debug_mode
        )
    elif agent_id == AgentType.AGNO_ASSIST:
        return get_agno_assist_simple(
            model_id=model_id,
            user_id=user_id,
            session_id=session_id,
            debug_mode=debug_mode
        )
    elif agent_id == AgentType.FINANCE_AGENT:
        return get_finance_agent(
            model_id=model_id,
            user_id=user_id,
            session_id=session_id,
            debug_mode=debug_mode
        )

    raise ValueError(f"Agent: {agent_id} not found")
