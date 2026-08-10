from pydantic import BaseModel
from typing import List

class AgentInfo(BaseModel):
    name: str
    role: str
    description: str

class AgentRosterResponse(BaseModel):
    agents: List[AgentInfo]
