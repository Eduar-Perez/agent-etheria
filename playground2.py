from fastapi import FastAPI
from agno.agent import Agent
from agno.models.aws import Claude
from agno.app.fastapi.app import FastAPIApp, HTTPException
from agno.app.fastapi.serve import serve_fastapi_app
from secrets_loader import load_aws_secrets
from pydantic import BaseModel
from mangum import Mangum
import uvicorn
import os
from dotenv import load_dotenv
from fastapi.responses import JSONResponse
from typing import Any

#PARA OBTENER VARIBLES DEL FILE .env 
load_dotenv()

#PARA OBTENER SECRETS MANAGER DE AWS
#load_aws_secrets()

MODELS = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"

class QuestionsRequest(BaseModel):
    question: str
    model_id: str

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

def create_api_fastapi_app(agent: Agent) -> FastAPIApp:
    app_wrapper = FastAPI(agent = agent)
    app = app_wrapper if isinstance(app_wrapper, FastAPI) else app_wrapper.app
    
    @app.post("/task")
    async def ask_question(request: QuestionsRequest):
        try:
            agent = agente_generico(request.model_id)
            response = agent.run(request.question)
            response_dict = safe_serialize(response)
            return JSONResponse(content={"response": response_dict})
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    return app

# def main():
#     try:
#         agent = agente_generico(model_id=MODELS)
#         fastapi_app = create_api_fastapi_app(agent)
#         app = fastapi_app if isinstance(fastapi_app, FastAPI) else fastapi_app.app
        
#        # Set the title and description of the FastAPI app
#         serve_fastapi_app(app = app, host = "0.0.0.0", port = 8001, reload = False)
#     except Exception as e:
#         print(f"Error: {e}")
#         return 1

if __name__ == "__main__":
    agent = agente_generico(MODELS)
    app = create_api_fastapi_app(agent)
    uvicorn.run(app, host="0.0.0.0", port=8080)
    main()
    #handler = Mangum(app)
