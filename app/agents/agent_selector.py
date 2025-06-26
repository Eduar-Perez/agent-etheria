from typing import Optional, Union, Callable
from app.agents.agent_type import AgentType
from app.agents.web_agent import get_web_agent_simple
from app.agents.agno_assist import get_agno_assist_simple
from app.agents.finance_agent import get_finance_agent
from app.agents.claude_agent import get_claud_agent


# Diccionario para mapear y construit cada tipo de agente
AGENT_MAP: dict[AgentType, Callable] = {
    AgentType.WEB_AGENT: get_web_agent_simple,
    AgentType.AGNO_ASSIST: get_agno_assist_simple,
    AgentType.FINANCE_AGENT: get_finance_agent,
    AgentType.CLAUD_AGENT: get_claud_agent
}

def get_agent(
    model: str = "gpt-4.1",
    agent_id: Optional[Union[AgentType, str]] = None,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    debug_mode: bool = True,
    instruction_user: Optional[str] = None,
    description_user: Optional[str] = None
    
    # file_name: Optional[str] = None,
    # file_content: Optional[str] = None
    
):
    if agent_id is None:
        raise ValueError("Agent ID must be provided")

    # Si viene como string, conviértelo al enum AgentType
    if isinstance(agent_id, str):
        try:
            agent_id = AgentType(agent_id)
        except ValueError:
            raise ValueError(f"Unknown agent ID: {agent_id}")

    # Seleccion de función desde el diccionario
    constructor = AGENT_MAP.get(agent_id)
    if constructor is None:
        raise ValueError(f"Agent: {agent_id} not found")

    # Llamar la función correspondiente
    return constructor(
        model_id=model,
        user_id=user_id,
        session_id=session_id,
        debug_mode=debug_mode,
        instruction_user=instruction_user,
        description_user=description_user
        # file_name=file_name,
        # file_content=file_content
    )
