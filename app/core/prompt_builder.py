# app/core/prompt_builder.py

import base64
import mimetypes
import io
from typing import Any
import json
from PIL import Image
import pytesseract
import fitz  # PyMuPDF
import docx

from models.request_models import QuestionsRequest


def build_prompt(request: QuestionsRequest) -> str:
    """Construye el prompt combinando la pregunta y los archivos adjuntos"""
    files_block = ""
    if request.files:
        file_texts = []
        for f in request.files:
            try:
                file_bytes = base64.b64decode(f.file)
                file_content = extract_file_from_bytes(file_bytes, f.fileName)
                file_texts.append(f"--- Archivo: {f.fileName} ---\n{file_content}")
            except Exception:
                file_texts.append(f"--- Archivo: {f.fileName} ---\n[Contenido binario no mostrado]")
        files_block = "ARCHIVOS ADJUNTOS:\n" + "\n\n".join(file_texts)

    return f"""{files_block}\nPREGUNTA:\n{request.question.strip()}"""


def extract_file_from_bytes(file_bytes: bytes, file_name: str) -> str:
    """Extrae el texto de un archivo según su tipo MIME"""
    mime_type, _ = mimetypes.guess_type(file_name)

    try:
        if mime_type == "application/pdf":
            with fitz.open(stream=file_bytes, filetype="pdf") as doc:
                return "\n".join(page.get_text() for page in doc)

        elif mime_type in [
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/msword",
        ]:
            doc = docx.Document(io.BytesIO(file_bytes))
            return "\n".join(p.text for p in doc.paragraphs)

        elif mime_type and mime_type.startswith("image/"):
            image = Image.open(io.BytesIO(file_bytes))
            return pytesseract.image_to_string(image)

        elif mime_type == "text/plain":
            return file_bytes.decode("utf-8", errors="replace")

    except Exception as e:
        raise ValueError(f"Error procesando '{file_name}': {e}")

    raise ValueError(f"Tipo de archivo no soportado: {mime_type or file_name}")


# def safe_serialize(obj: Any):
#     """Convierte cualquier objeto a un dict serializable por JSON"""
#     if isinstance(obj, (str, int, float, bool)) or obj is None:
#         return obj
#     elif isinstance(obj, dict):
#         return {k: safe_serialize(v) for k, v in obj.items()}
#     elif isinstance(obj, list):
#         return [safe_serialize(v) for v in obj]
#     elif hasattr(obj, "__dict__"):
#         return safe_serialize(vars(obj))
#     else:
#         return str(obj)
def safe_serialize(obj):
    try:
        if isinstance(obj, str):
            return obj
        return json.loads(json.dumps(obj, ensure_ascii=False))
    except Exception as e:
        print(f"⚠️ Error en safe_serialize: {e}")
        return str(obj)
