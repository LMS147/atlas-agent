"""Wire models matching android/data/model/ApiModels.kt."""
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator

Section = Literal["User Preferences", "Projects", "Decisions", "People"]

class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: str = Field(min_length=1, max_length=8000)
    conversation_id: str = Field(min_length=1, max_length=128, pattern=r"^[a-zA-Z0-9._:-]+$")
    request_id: UUID

    @field_validator("message")
    @classmethod
    def nonblank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Message cannot be blank")
        return value

class ChatReply(BaseModel):
    reply: str

class MemoryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    section: Section
    fact: str = Field(min_length=1, max_length=300)

    @field_validator("fact")
    @classmethod
    def normalize(cls, value: str) -> str:
        value = " ".join(value.split())
        if not value:
            raise ValueError("Fact cannot be blank")
        return value

class MemoryItem(BaseModel):
    id: str
    section: str
    fact: str

class AgentProfile(BaseModel):
    name: str = "Atlas"
    content: str

class FileItem(BaseModel):
    name: str
    path: str
    directory: bool
    size_bytes: int = 0

class Health(BaseModel):
    status: str = "ok"
    version: str = "0.2.0"
    uptime_seconds: int
