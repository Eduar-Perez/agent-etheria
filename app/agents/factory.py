# agents/factory.py

from agno.tools.yfinance import YFinanceTools
from .base_agent_factory import BaseAgentFactory

AGENTS = {
    "web_agent": BaseAgentFactory(
        agent_id="web_agent",
        name="Web Search Agent",
        prompt_file="./agents/prompts/web_agent.txt",
        description_file="./agents/prompts/web_agent_description.txt",
        default_model="gpt-4.1",
        extra_tools=[],
        state_enabled=True,
    ),
    "agno_assist": BaseAgentFactory(
        agent_id="agno_assist",
        name="Agno Assist",
        prompt_file="./agents/prompts/agno_assist.txt",
        description_file="./agents/prompts/agno_assist_description.txt",
    ),
    "finance_agent": BaseAgentFactory(
        agent_id="finance_agent",
        name="Finance Agent",
        prompt_file="./agents/prompts/finance_agent.txt",
        description_file="./agents/prompts/finance_agent_description.txt",
        extra_tools=[
            YFinanceTools(
                stock_price=True,
                analyst_recommendations=True,
                stock_fundamentals=True,
                historical_prices=True,
                company_info=True,
                company_news=True,
            )
        ],
        memory_enabled=False,
        state_enabled=False,
    ),
    "claude_agent": BaseAgentFactory(
        agent_id="claud_agent",
        name="Claud Agent",
        prompt_file="./agents/prompts/claude_agent.txt",
        description_file="./agents/prompts/claude_agent_description.txt",
    ),
    "code_agent": BaseAgentFactory(
        agent_id="code_agent",
        name="Code Agent",
        prompt_file="./agents/prompts/code_agent.txt",
        description_file="./agents/prompts/code_agent_description.txt",
    ),
        "flow_chart_agent": BaseAgentFactory(
        agent_id="flow_chart_agent",
        name="Flow Chart Agent",
        prompt_file="./agents/prompts/flow_chart_agent.txt",
        description_file="./agents/prompts/flow_chart_agent_description.txt",
    ),
    "intro": BaseAgentFactory(
        agent_id="intro",
        name="introduction",
        prompt_file="./agents/prompts/intro_datastage.txt",
        description_file="./agents/prompts/intro_datastage_description.txt",
    ),
    
    "section_1_agent": BaseAgentFactory(
        agent_id="section_1_agent",
        name="section_1_agent",
        prompt_file="./agents/prompts/section_1_agent.txt",
        description_file="./agents/prompts/section_1_agent_description.txt",
    ),
    
    "description_agent": BaseAgentFactory(
        agent_id="description_agent",
        name="description_agent",
        prompt_file="./agents/prompts/descripcion_por_jobs.txt",
        description_file="./agents/prompts/descripcion_por_jobs.txt",
    )
}
