from pydantic import BaseModel
from typing import Optional, List

class InstructionItem(BaseModel):
    intruction: str  # Ojo: aquí se mantiene el typo si el front lo envía así
    description: Optional[str] = None

class FileItem(BaseModel):
    file: str        # contenido base64
    fileName: str

class QuestionsRequest(BaseModel):
    question: str
    model: Optional[str] = None
    agent_id: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    instructions: Optional[List[InstructionItem]] = None
    files: Optional[List[FileItem]] = None
    tool: Optional[bool] = None
