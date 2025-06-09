from textwrap import dedent
from typing import Optional
from agno.agent import Agent
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.models.aws import Claude

def get_agno_assist_simple(
    model_id: str = "gpt-4.1",
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    debug_mode: bool = True,
) -> Agent:
    return Agent(
        name="Agno Assist",
        agent_id="agno_assist",
        user_id=user_id,
        session_id=session_id,
        model_id=Claude(id=model_id),
        tools=[DuckDuckGoTools()],
        description=dedent("""\
            You are AgnoAssist, an advanced AI Agent specializing in Agno: a lightweight framework for building multi-modal, reasoning Agents.

            Your goal is to help developers understand and use Agno by providing clear explanations, functional code examples, and best-practice guidance for using Agno.
        """),
        instructions=dedent(f"""\
            Your mission is to provide comprehensive and actionable support for developers working with the Agno framework. Follow these steps to deliver high-quality assistance:

            1. Understand the request and analyze it properly.
            2. Use the tools available to gather the best information.
            3. Provide clear, concise, and correct explanations and examples.

            Additional Information:
            - You are interacting with the user_id: {user_id}
        """),
        storage=None,
        add_history_to_messages=False,
        read_chat_history=False,
        enable_agentic_memory=False,
        markdown=True,
        add_datetime_to_instructions=True,
        debug_mode=debug_mode,
    )
