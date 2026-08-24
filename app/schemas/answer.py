from pydantic import BaseModel, Field
from typing import List, Optional

class QuestionEnvelope(BaseModel):
    question_id: str
    client_id: Optional[str] = None
    prompt: str
    deadline_seconds: Optional[int] = 60
    progress: Optional[dict] = None

class AnswerResponse(BaseModel):
    question_id: str
    client_id: Optional[str] = None
    answer: str                         # Required string field for validator!
    answer_value: Optional[str] = None  # Exact extracted answer value or null
    abstained: bool = False
    refused: bool = False
    reason: Optional[str] = None        # Refusal reason or null
    citations: List[str] = Field(default_factory=list)  # List of citation strings
    confidence: float = 1.0             # Float between 0.0 and 1.0
    flags: List[str] = Field(default_factory=list)      # Allowed: conflict, upstream_issue, stale_data
    agents: List[str] = Field(default_factory=list)     # List of role strings
