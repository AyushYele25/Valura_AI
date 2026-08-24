from pydantic import BaseModel
from typing import List, Optional

class AgentInfo(BaseModel):
    name: str
    role: str
    description: str

class AgentRosterResponse(BaseModel):
    framework: str = "agno"
    framework_version: Optional[str] = None
    agents: List[AgentInfo]
