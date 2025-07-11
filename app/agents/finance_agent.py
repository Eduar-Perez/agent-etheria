from textwrap import dedent
from typing import Optional
from agno.models.aws import Claude
from agno.agent import Agent
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.yfinance import YFinanceTools
from utilities.get_prompts import open_prompt

def get_finance_agent(
    model_id: str = "gpt-4.1",
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    debug_mode: bool = False,
    instruction_user: Optional[str] = None,
    description_user: Optional[str] = None,
    tools_input: Optional[bool] = None
) -> Agent:
    """
    Crea y devuelve el agente financiero configurado.
    """
    instructions_hardcode = open_prompt("./agents/prompts/finance_agent.txt")
    instructions_hardcode = instructions_hardcode.format(current_user_id=user_id)
    instructions_end = (
        dedent(instruction_user) if instruction_user else instructions_hardcode
    )
    descriptions_hardcode = open_prompt("./agents/prompts/finance_agent_description.txt")
    description_end = (
        dedent(description_user) if description_user else descriptions_hardcode
    )
    return Agent(
        name="Finance Agent",
        agent_id="finance_agent",
        user_id=user_id,
        session_id=session_id,
        model=Claude(id=model_id),
        tools=[
            DuckDuckGoTools(),
            YFinanceTools(
                stock_price=True,
                analyst_recommendations=True,
                stock_fundamentals=True,
                historical_prices=True,
                company_info=True,
                company_news=True,
            ),
        ],
        description=description_end,
        instructions=instructions_end,
        add_state_in_messages=True,
        # Quitamos storage para evitar dependencia a BD
        # add_history_to_messages=True,
        # num_history_runs=3,
        # read_chat_history=True,
        enable_agentic_memory=True,
        markdown=True,
        add_datetime_to_instructions=True,
        debug_mode=debug_mode,
    )


def run_agent(query: str, model_id: str = "gpt-4.1") -> str:
    """
    Función para ejecutar el agente financiero con una consulta.
    """
    agent = get_finance_agent(model_id=model_id)
    response = agent.run(query)
    return response
