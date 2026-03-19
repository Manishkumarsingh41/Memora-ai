from pydantic import BaseModel
from typing import Optional

class WhatsAppMessage(BaseModel):
    from_number: str
    message_id: str
    message_type: str
    text: Optional[str] = None

class FileMetadata(BaseModel):
    id: Optional[int] = None
    user_id: str
    file_name: str
    file_type: str
    drive_file_id: str
    folder: str
    created_at: Optional[str] = None

class PendingUpload(BaseModel):
    user_id: str
    media_id: str
    media_mime_type: str
    original_filename: str
    file_type: str
    awaiting: str = "action"

class MemoryEntry(BaseModel):
    role: str
    content: str
    created_at: Optional[str] = None

class AgentResponse(BaseModel):
    intent: str
    response_text: str
    file_query: Optional[str] = None
    file_number: Optional[int] = None
    rag_query: Optional[str] = None
