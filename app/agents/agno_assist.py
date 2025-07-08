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
    instruction_user: Optional[str] = None,
    description_user: Optional[str] = None,
    tools_input: Optional[bool] = None
) -> Agent:
    instructions_hardcode = dedent(f"""\                
            🟢 IMPORTANTE:
            - Siempre responde en **español**, sin importar el idioma original de la pregunta del usuario.
            - Si detectas que la pregunta está en inglés u otro idioma, primero **tradúcela internamente al español**, y luego responde únicamente en español.
            - Si el usuario escribe en inglés, puedes incluir una nota breve: "(Traducción automática del inglés)" al inicio de tu respuesta.                               
            
            Your mission is to provide comprehensive and actionable support for developers working with the Agno framework. Follow these steps to deliver high-quality assistance:

            1. Understand the request and analyze it properly.
            2. Use the tools available to gather the best information.
            3. Provide clear, concise, and correct explanations and examples.

            Additional Information:
            - You are interacting with the user_id: {user_id}
        """)
    instructions_end = dedent(instruction_user) if instruction_user else instructions_hardcode
    descriptions_hardcode = dedent("""\            
            You are AgnoAssist, an advanced AI Agent specializing in Agno: a lightweight framework for building multi-modal, reasoning Agents.

            Your goal is to help developers understand and use Agno by providing clear explanations, functional code examples, and best-practice guidance for using Agno.
        """)
    description_end = dedent(description_user) if description_user else descriptions_hardcode
    return Agent(
        name="Agno Assist",
        agent_id="agno_assist",
        user_id=user_id,
        session_id=session_id,
        model=Claude(id=model_id),
        tools=[DuckDuckGoTools()],
        description=description_end,
        instructions=instructions_end,
        storage=None,
        add_history_to_messages=False,
        read_chat_history=False,
        enable_agentic_memory=False,
        markdown=True,
        add_datetime_to_instructions=True,
        debug_mode=debug_mode,
    )
