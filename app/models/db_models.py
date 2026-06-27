from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime, timezone

class Meeting(SQLModel, table=True):
    """A single uploaded meeting (audio or text)."""
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    original_filename: str
    input_type: str                       # "audio" | "text"
    file_path: str                        # where the raw file is saved
    transcript: Optional[str] = None      # raw text (from Whisper or user input)
    summary: Optional[str] = None   # LLM generated summary
    status: str = Field(default="pending")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


    action_items: List["ActionItem"] = Relationship(back_populates="meeting")

class ActionItem(SQLModel, table=True):
    """One extracted action item, linked to a meeting"""
    id: Optional[int] = Field(default=None, primary_key=True)
    meeting_id: int = Field(foreign_key="meeting.id")
    task: str
    owner: Optional[str] = None
    priority: str = Field(default="Medium")   # High | Medium | Low
    deadline: Optional[str] = None
    status: str = Field(default="open")       # open | in_progress | done
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    meeting: Optional[Meeting] = Relationship(back_populates="action_items")

# ── API Response Schemas ──────────────────────────────────────
# These reuse the same fields but shape the JSON returned by FastAPI
class ActionItemOut(SQLModel):
    id: int
    task: str
    owner: Optional[str]
    priority: str
    deadline: Optional[str]
    status: str


class MeetingOut(SQLModel):
    id: int
    title: str
    original_filename: str
    input_type: str
    summary: Optional[str]
    status: str
    created_at: datetime
    action_items: List[ActionItemOut] = []

class ActionItemUpdate(SQLModel):
    """Fields a user can update via PATCH /update-action/{id}"""
    status: Optional[str] = None
    priority: Optional[str] = None
    owner: Optional[str] = None
    deadline: Optional[str] = None