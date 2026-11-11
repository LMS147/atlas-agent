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
    require_existing: bool = False

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
    writable: bool = False

class Health(BaseModel):
    streaming_chat: bool = True
    status: str = "ok"
    version: str = "0.5.0"
    uptime_seconds: int
    pid: int = 0

class ConversationName(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(default="New chat", min_length=1, max_length=80)

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str) -> str:
        value = " ".join(value.split())
        if not value:
            raise ValueError("Title cannot be blank")
        return value

class ConversationItem(BaseModel):
    id: str
    title: str
    created_at: int
    updated_at: int
    message_count: int
    preview: str
    deleted: bool = False

class TranscriptMessage(BaseModel):
    seq: int
    id: str
    request_id: str
    role: Literal["user", "assistant"]
    text: str
    created_at: int

class MessagePage(BaseModel):
    items: list[TranscriptMessage]
    has_more: bool
    next_before: int | None

class ChatRequestStatus(BaseModel):
    request_id: str
    status: Literal["not_found", "pending", "done", "failed", "interrupted"]
    reply: str | None = None

class FileEdit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    content: str = Field(max_length=262144)
    revision: str = Field(pattern=r"^[0-9a-f]{64}$")

class CompactRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    revision: str = Field(pattern=r"^[0-9a-f]{64}$")
