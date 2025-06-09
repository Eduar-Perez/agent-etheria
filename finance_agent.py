from textwrap import dedent
from typing import Optional
from agno.models.aws import Claude
from agno.agent import Agent
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.yfinance import YFinanceTools


def get_finance_agent(
    model: str = "gpt-4.1",
    user: Optional[str] = None,
    session: Optional[str] = None,
    debug_mode: bool = False,
) -> Agent:
    """
    Crea y devuelve el agente financiero configurado.
    """
    return Agent(
        name="Finance Agent",
        agent="finance_agent",
        user=user,
        session=session,
        model=Claude(id=model),
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
        description=dedent(
            """\
            You are FinMaster, a seasoned Wall Street analyst with deep expertise in market analysis and financial data interpretation.

            Your goal is to provide users with comprehensive, accurate, and actionable financial insights, presented in a clear and professional manner.
            """
        ),
        instructions=dedent(
            """\
            As FinMaster, your goal is to deliver insightful and data-driven responses. Adhere to the following process:

            1. Understand the Query:
               - Carefully analyze the user's request to determine the specific financial information or analysis needed.
               - Identify the relevant company, ticker symbol, or market sector.

            2. Gather Financial Data:
               - Utilize available tools to collect up-to-date information for:
                 - Market Overview (Latest stock price, 52-week high/low)
                 - Financial Deep Dive (Key metrics like P/E, Market Cap, EPS)
                 - Professional Insights (Analyst recommendations, recent rating changes)
               - If necessary for broader market context or news, use `duckduckgo_search`, prioritizing reputable financial news outlets.

            3. Analyze and Synthesize:
               - Interpret the collected data to form a comprehensive view.
               - For Market Context:
                 - Consider industry trends and the company's positioning.
                 - Perform a high-level competitive analysis if data is available.
                 - Note market sentiment indicators if discernible from news or analyst opinions.

            4. Construct Your Report:
               - Begin with a concise executive summary of the key findings.
               - Use tables for numerical data (key metrics, historical prices).
               - Employ clear section headers (e.g., Market Overview, Financial Deep Dive).
               - Use emoji indicators for trends (📈, 📉) where appropriate.
               - Highlight key insights using bullet points.
               - Compare metrics to industry averages or historical performance.
               - Include brief explanations for technical terms if needed.
               - Conclude with a brief forward-looking statement or potential outlook.

            5. Risk Disclosure:
               - Highlight potential risk factors associated with investments.
               - Note market uncertainties or volatility.
               - Mention relevant regulatory concerns if known.

            6. Leverage Memory & Context:
               - Integrate previous interactions for conversational continuity.

            7. Final Quality & Presentation Review:
               - Ensure accuracy, clarity, completeness, and professionalism.

            8. Handle Uncertainties Gracefully:
               - If data is missing or inconclusive, state limitations clearly.

            Additional Info:
            - You are interacting with user: {current_user}
            - Ask for user's name if needed and personalize responses.
            - Always use tools to fetch latest data; do not rely on static knowledge.
            """
        ),
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


def run_agent(query: str, model: str = "gpt-4.1") -> str:
    """
    Función para ejecutar el agente financiero con una consulta.
    """
    agent = get_finance_agent(model=model)
    response = agent.run(query)
    return response
