"""
Router: POST /upload-meeting
------------------------------
Accepts either:
  - Audio file (.mp3 .wav .m4a .ogg .mp4)
  - Text file  (.txt .md)
  - Raw text pasted directly

Saves file via Filesystem MCP → creates Meeting in DB
→ kicks off agent pipeline as a background task
→ returns immediately with the meeting ID

Why return immediately?
  The pipeline takes 30-60 seconds (Whisper + 2 LLM calls).
  We don't make the user wait — they get the meeting ID instantly
  and poll for results separately.
"""

from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, BackgroundTasks, HTTPException, Depends
from sqlmodel import Session

from app.models.db_models import Meeting, MeetingOut
from app.models.database import get_session
from app.mcp.filesystem_mcp import save_file
from app.agents.pipeline import run_pipeline
from app.config import settings


router = APIRouter(prefix="/upload-meeting", tags=["upload"])

AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".mp4"}
TEXT_EXTENSIONS  = {".txt", ".md"}


@router.post("/", response_model=MeetingOut)
async def upload_meeting(
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
    title: str = Form(...),
    file: UploadFile | None = File(default=None),
    text_input: str | None = Form(default=None),
):
    """
    Upload a meeting (audio or text) and start the agent pipeline.

    Form fields:
        title      : meeting title (required)
        file       : audio or text file (optional)
        text_input : raw pasted text (optional)

    Either file or text_input must be provided.
    """

    # ── Validate input ────────────────────────────────────────
    if not file and not text_input:
        raise HTTPException(
            status_code=400,
            detail="Provide either a file upload or paste text in text_input"
        )

    # ── Determine input type from file extension ──────────────
    if file:
        ext = Path(file.filename).suffix.lower()
        if ext in AUDIO_EXTENSIONS:
            input_type = "audio"
        elif ext in TEXT_EXTENSIONS:
            input_type = "text"
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type '{ext}'. Supported: {AUDIO_EXTENSIONS | TEXT_EXTENSIONS}"
            )
    else:
        # Raw pasted text
        input_type = "text"
        ext = ".txt"

    # ── Create Meeting record in DB ───────────────────────────
    # Create it first so we have an ID to use for file naming
    filename = file.filename if file else f"{title.replace(' ', '_')}.txt"
    meeting = Meeting(
        title=title,
        original_filename=filename,
        input_type=input_type,
        file_path="",           # filled in after save below
        status="pending",
    )
    session.add(meeting)
    session.commit()
    session.refresh(meeting)    # populates meeting.id

    # ── Save file via Filesystem MCP ──────────────────────────
    relative_path = f"meetings/{meeting.id}_{filename}"
    audio_path_for_pipeline = None

    if file:
        content_bytes = await file.read()

        if input_type == "audio":
            # Audio files are binary — write directly to disk
            # Whisper needs a real file path, not a string
            abs_path = Path(settings.MEETINGS_DIR) / f"{meeting.id}_{filename}"
            abs_path.parent.mkdir(parents=True, exist_ok=True)
            abs_path.write_bytes(content_bytes)
            saved_path = str(abs_path)
            audio_path_for_pipeline = saved_path   # passed to pipeline

        else:
            # Text file — decode and save via MCP
            content_str = content_bytes.decode("utf-8")
            meeting.transcript = content_str
            saved_path = await save_file(relative_path, content_str)

    else:
        # Raw pasted text — save via MCP
        meeting.transcript = text_input
        saved_path = await save_file(relative_path, text_input)

    # ── Update meeting with saved path ────────────────────────
    meeting.file_path = saved_path
    session.add(meeting)
    session.commit()
    session.refresh(meeting)

    # ── Kick off pipeline in background ──────────────────────
    # add_task() returns immediately — pipeline runs after response is sent
    background_tasks.add_task(
        run_pipeline,
        meeting.id,
        audio_path_for_pipeline,    # None if text input
    )

    # Return meeting immediately — status will be "pending"
    # UI polls /meetings/{id}/status to track progress
    return meeting