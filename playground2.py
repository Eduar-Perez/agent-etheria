from fastapi import FastAPI, HTTPException
from agno.agent import Agent
from agno.models.aws import Claude
from secrets_loader import load_aws_secrets
from pydantic import BaseModel
from mangum import Mangum
import uvicorn
from fastapi.responses import JSONResponse
from typing import Any, Optional
from agent_selector import get_agent, AgentType

# PARA OBTENER SECRETS MANAGER DE AWS
load_aws_secrets()

MODELS = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"

class QuestionsRequest(BaseModel):
    question: str
    model: str
    agent_id: str  # corregido de "agent" a "agent_id"
    user_id: Optional[str] = None  # corregido de "user"
    session_id: Optional[str] = None  # corregido de "session"


def agente_generico(model_id: str) -> Agent:
    return Agent(
        name="Claude Agent",
        model=Claude(id=model_id),
        show_tool_calls=True,
        markdown=True,
        debug_mode=True
    )


def safe_serialize(obj: Any):
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    elif isinstance(obj, dict):
        return {k: safe_serialize(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [safe_serialize(v) for v in obj]
    elif hasattr(obj, "__dict__"):
        return safe_serialize(vars(obj))
    else:
        return str(obj)


def create_api_fastapi_app(agent: Agent) -> FastAPI:
    app = FastAPI()
    
    @app.post("/task")
    async def ask_question(request: QuestionsRequest):
        try:
            agent_enum = AgentType(request.agent_id)
            agent = get_agent(
                model=request.model,
                agent_id=agent_enum,
                user_id=request.user_id,
                session_id=request.session_id,
                debug_mode=True
            )   
            response = agent.run(request.question)
            response_dict = safe_serialize(response)
            return JSONResponse(content={"response": response_dict})
        except ValueError as ve:
            raise HTTPException(status_code=400, detail=str(ve))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    return app


agent = agente_generico(MODELS)
app = create_api_fastapi_app(agent)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
