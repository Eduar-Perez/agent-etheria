from fastapi import FastAPI
from agno.agent import Agent
from agno.models.aws import Claude
from fastapi import FastAPI
from fastapi import HTTPException
#from agno.app.fastapi.serve import serve_fastapi_app
from secrets_loader import load_aws_secrets
from pydantic import BaseModel
from mangum import Mangum
import uvicorn
import os
import boto3
from dotenv import load_dotenv
from fastapi.responses import JSONResponse
from typing import Any, Optional
from agent_selector import get_agent, AgentType

#PARA OBTENER VARIBLES DEL FILE .env 
#load_dotenv()

#PARA OBTENER SECRETS MANAGER DE AWS
load_aws_secrets()

MODELS = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"

class QuestionsRequest(BaseModel):
    question: str
    model: str
    agent: str
    user: Optional[str] = None
    session: Optional[str] = None


def agente_generico(model_id: str) -> Agent:
    agent_Claude = Agent(
        name="Claude Agent",
        model=Claude(id=model_id),
        show_tool_calls=True,
        markdown=True,
        debug_mode=True
    )
    return agent_Claude

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
        return str(obj)  # Último recurso: convertir a string

def create_api_fastapi_app(agent: Agent) -> FastAPI:
    app = FastAPI()
    
    @app.post("/task")
    async def ask_question(request: QuestionsRequest):
        try:
            agent_enum = AgentType(request.agent_id)
            agent = get_agent(
                model = request.model_id,
                agent = agent_enum,
                user = request.user_id,
                session = request.session_id,
                debug_mode = True
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
