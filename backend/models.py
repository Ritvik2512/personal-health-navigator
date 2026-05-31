from pydantic import BaseModel
from typing import List, Dict, Any, Optional


class Message(BaseModel):
    role: str           # "user" or "model"
    parts: List[Dict[str, Any]]


class ChatRequest(BaseModel):
    message: str
    history: List[Message] = []


class ChatResponse(BaseModel):
    reply: str
    updated_history: List[Dict]
    emergency: bool = False
    emergency_reason: Optional[str] = None
    tool_calls_made: List[str] = []
