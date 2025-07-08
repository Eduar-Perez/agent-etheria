import uvicorn
import base64
import mimetypes
import pytesseract
import fitz
import docx
from PIL import Image
import io
from fastapi import FastAPI, HTTPException
from agno.agent import Agent
from agno.models.aws import Claude
from secrets_loader import load_aws_secrets
from pydantic import BaseModel
from mangum import Mangum
from fastapi.responses import JSONResponse
from typing import Any, Optional, List
from agents.agent_selector import get_agent, AgentType
from dotenv import load_dotenv
import logging
import traceback
from fastapi import Request
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# PARA OBTENER SECRETS MANAGER DE AWS
load_aws_secrets()
# # PARA OBTENER VATRIABLES DE ENTORNO DE .env
# load_dotenv()

MODELS = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"


class InstructionItem(BaseModel):
    instruction: str
    description: Optional[str] = None


class FileItem(BaseModel):
    file: str  # base64
    fileName: str


class QuestionsRequest(BaseModel):
    question: str
    model: str
    agent_id: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    instructions: Optional[List[InstructionItem]] = None
    files: Optional[List[FileItem]] = None


def agente_generico(model_id: str) -> Agent:
    """Crea un agente genérico con el modelo especificado."""
    return Agent(
        name="Claude Agent",
        model=Claude(id=model_id),
        show_tool_calls=True,
        markdown=True,
        debug_mode=True,
        # fileName=None,
        # file=None
    )


# Crea el prompt para la pregunta
def build_prompt(request: QuestionsRequest) -> str:
    # Archivos
    files_block = ""
    if request.files:
        file_texts = []
        for f in request.files:
            try:
                file_bytes = base64.b64decode(f.file)
                file_content = extractFileFromBytes(file_bytes, f.fileName)
                file_texts.append(f"--- Archivo: {f.fileName} ---\n{file_content}")
            except Exception:
                file_texts.append(
                    f"--- Archivo: {f.fileName} ---\n[Contenido binario no mostrado]"
                )
        files_block = "ARCHIVOS ADJUNTOS:\n" + "\n\n".join(file_texts)
    # Solo archivos + pregunta
    return f"""{files_block}

PREGUNTA:
{request.question.strip()}
"""


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


def extractFileFromBytes(file_byts: bytes, file_name: str) -> str:
    mime_type, _ = mimetypes.guess_type(file_name)
    if mime_type == "application/pdf":
        with fitz.open(stream=file_byts, file_name="pdf") as doc:
            return "\n".join(page.get_text() for page in doc)

    elif mime_type in [
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
    ]:
        # with open("temp.docx", "wb") as temp:
        #     temp.write(file_byts)
        doc = docx.Document(io.BytesIO(file_byts))
        return "\n".join(p.text for p in doc.paragraphs)

    elif mime_type and mime_type.startswith("image/"):
        image = Image.open(io.BytesIO(file_byts))
        return pytesseract.image_to_string(image)
    raise ValueError("Tipo de archivo no soportado")


def create_api_fastapi_app() -> FastAPI:
    fastapi_app = FastAPI()
    @fastapi_app.middleware("http")
    async def log_raw_request(request: Request, call_next):
        try:
            body = await request.body()
            logging.info("Raw incoming request body:\n%s", body.decode("utf-8"))
        except Exception as e:
            logging.error("Failed to read request body: %s", str(e))
        response = await call_next(request)
        return response
    @fastapi_app.post("/task")
    async def ask_question(request: QuestionsRequest):
        logging.info(f"Received request: {request}")
        try:
            logging.info(
                "Received request for agent=%s, model=%s, question=%s,\
                instructions=%s",
                request.agent_id,
                request.model,
                request.question[:50],
                request.instructions,
            )
            instructions_user = None
            description_user = None
            if request.instructions:
                lines = []
                for i in request.instructions:
                    inst = getattr(i, "intruction", None)
                    if inst:
                        line = f"- {inst}"
                        if i.description:
                            line += f" ({i.description})"
                        lines.append(line)
                instructions_user = "\n".join(lines)
                description_user = request.instructions[0].description or None
            agent_enum = AgentType(request.agent_id)
            agent = get_agent(
                model=request.model,
                agent_id=agent_enum,
                user_id=request.user_id,
                session_id=request.session_id,
                debug_mode=True,
                instruction_user=instructions_user,
                description_user=description_user,
                tools_input=False,
            )
            input_prompt = build_prompt(request)
            response = agent.run(input_prompt)
            response_dict = safe_serialize(response)
            final_response = JSONResponse(content={"response": response_dict})
            logging.info(f"Final response: {final_response}")
            return final_response
        except ValueError as ve:
            raise HTTPException(status_code=400, detail=str(ve))
        except Exception as e:
            logging.error("Unhandled Exception:\n%s", traceback.format_exc())
            raise HTTPException(status_code=500, detail=str(e))

    return fastapi_app

app = create_api_fastapi_app()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8081)
