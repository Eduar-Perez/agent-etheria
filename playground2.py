import uvicorn
import base64
import mimetypes
import fitz
import docx
from PIL import Image
import pytesseract
import io
from fastapi import FastAPI, HTTPException
from agno.agent import Agent
from agno.models.aws import Claude
from secrets_loader import load_aws_secrets
from pydantic import BaseModel
from mangum import Mangum
from fastapi.responses import JSONResponse
from typing import Any, Optional
from agent_selector import get_agent, AgentType
from dotenv import load_dotenv

# PARA OBTENER SECRETS MANAGER DE AWS
#load_aws_secrets()
# PARA OBTENER VATRIABLES DE ENTORNO DE .env
load_dotenv()

MODELS = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"

class QuestionsRequest(BaseModel):
    question: str
    model: str
    agent_id: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    file: Optional[str] = None
    fileName: Optional[str] = None


def agente_generico(model_id: str) -> Agent:
    return Agent(
        name="Claude Agent",
        model=Claude(id=model_id),
        show_tool_calls=True,
        markdown=True,
        debug_mode=True,
        fileName=None,
        file=None
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

            file_base64 = None
            if request.file:
                try:
                    fileBytes = base64.b64decode(request.file)
                    fileName = request.fileName
                    extractedText = extractFileFromBytes(fileBytes, fileName)
                    request.question = f"Analiza el siguiente contenido del archivo:\n\n{extractedText}"
                except Exception as e:
                    raise HTTPException(status_code=400, detail=f"Archivo invalido o no procesable: {str(e)}")

            response = agent.run(request.question)
            response_dict = safe_serialize(response)
            return JSONResponse(content={"response": response_dict})
        except ValueError as ve:
            raise HTTPException(status_code=400, detail=str(ve))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    return app

def extractFileFromBytes(file_byts: bytes, file_name: str) -> str:
    mime_type, _ = mimetypes.guess_type(file_name)
    if mime_type == 'application/pdf':
        with fitz.open(stream=file_byts, file_name='pdf') as doc:
            return "\n".join(page.get_text() for page in doc)
        
    elif mime_type in ['application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'application/msword']:
        with open("temp.docx", "wb") as temp:
            temp.write(file_byts)
        doc = docx.Document(io.BytesIO(file_byts))
        return "\n".join(p.text for p in doc.paragraphs)

    elif mime_type and mime_type.startswith('image/'):
        image = Image.open(io.BytesIO(file_byts))
        return pytesseract.image_to_string(image)
    return ValueError("Tipo de retorno no soportado")

agent = agente_generico(MODELS)
app = create_api_fastapi_app(agent)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
