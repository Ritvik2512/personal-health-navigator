from pydantic import BaseModel
from typing import List, Dict, Any, Optional


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"
    history: List[Message] = []
    patient_context: Dict[str, Any] = {}


class ChatResponse(BaseModel):
    reply: str
    updated_history: List[Dict]
    patient_context: Dict[str, Any] = {}
    emergency: bool = False
    emergency_reason: Optional[str] = None
    tool_calls_made: List[str] = []
