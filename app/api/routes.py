import os
import json
from fastapi import Request, HTTPException, FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from models.request_models import QuestionsRequest
from agents.agent_selector import get_agent
from agents.agent_type import AgentType
from core.prompt_builder import build_prompt, safe_serialize
from utilities.team_manager import team_manager
import base64
import logging
import traceback


logger = logging.getLogger(__name__)

def configure_routes(app: FastAPI):
    @app.middleware("http")
    async def log_raw_request(request: Request, call_next):
        body = await request.body()
        logger.info("Request Body: %s", body.decode("utf-8"))
        return await call_next(request)
    @app.post("/task")
    async def ask_question(request: QuestionsRequest):
        try:
            type_agent = request.agent_id
            print("type_agent", type_agent)
            if type_agent[:5] == "team_":
                response = team_manager(request)
            else:
                
                instructions_user = None
                description_user = None
                if request.instructions:
                    lines = [
                        (
                            f"- {i.intruction} ({i.description})"
                            if i.description
                            else f"- {i.intruction}"
                        )
                        for i in request.instructions
                    ]
                    instructions_user = "\n".join(lines)
                    description_user = request.instructions[0].description

                agent_enum = AgentType(request.agent_id)
                agent = get_agent(
                    model=request.model,
                    agent_id=agent_enum,
                    user_id=request.user_id if request.user_id else "default_user",
                    session_id=request.session_id if request.session_id else "default_session", 
                    debug_mode=False,
                    instruction_user=instructions_user,
                    description_user=description_user,
                    tools_input=request.tool if request.tool is not None else False,
                )
                input_prompt = build_prompt(request)
                response = agent.run(input_prompt)
                response = response.content
            return JSONResponse(content={"response": safe_serialize(response)})
        except RequestValidationError as rve:
            print("rve", rve)
            raise HTTPException(status_code=422, detail=rve.errors()) from rve
        except ValueError as ve:
            raise HTTPException(status_code=400, detail=str(ve)) from ve
        except Exception as e:
            logger.error("Unhandled Exception:\n%s", traceback.format_exc())
            raise HTTPException(status_code=500, detail=str(e)) from e