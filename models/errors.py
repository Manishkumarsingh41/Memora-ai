from pydantic import BaseModel
from typing import Optional, List, Any

class ErrorDetail(BaseModel):
    field: Optional[str] = None
    message: str
    type: Optional[str] = None

class ErrorResponse(BaseModel):
    status: str = "error"
    code: int
    message: str
    details: Optional[List[ErrorDetail]] = None
