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
}
