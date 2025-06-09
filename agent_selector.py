from enum import Enum
from typing import List, Optional, Union

from agno_assist import get_agno_assist_simple
from finance_agent import get_finance_agent
from web_agent import get_web_agent_simple


class AgentType(Enum):
    WEB_AGENT = "web_agent"
    AGNO_ASSIST = "agno_assist"
    FINANCE_AGENT = "finance_agent"


def get_available_agents() -> List[str]:
    """Returns a list of all available agent IDs as strings."""
    return [agent.value for agent in AgentType]


def get_agent(
    model: str = "gpt-4.1",
    agent: Optional[Union[AgentType, str]] = None,
    user: Optional[str] = None,
    session: Optional[str] = None,
    debug_mode: bool = True,
):
    if agent is None:
        raise ValueError("Agent ID must be provided")

    # Si llega como string, convierto a AgentType
    if isinstance(agent, str):
        try:
            agent = AgentType(agent)
        except ValueError:
            raise ValueError(f"Unknown agent ID: {agent}")

    if agent == AgentType.WEB_AGENT:
        return get_web_agent_simple(model=model, user=user, session=session, debug_mode=debug_mode)
    elif agent == AgentType.AGNO_ASSIST:
        return get_agno_assist_simple(model=model, user=user, session=session, debug_mode=debug_mode)
    elif agent == AgentType.FINANCE_AGENT:
        return get_finance_agent(model=model, user=user, session=session, debug_mode=debug_mode)

    raise ValueError(f"Agent: {agent} not found")
