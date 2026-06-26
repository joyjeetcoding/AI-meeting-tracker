"""
Pipeline Orchestrator
----------------------
Chains all agents in sequence for a given meeting.

Flow:
  [if audio] Agent 1: Transcription  (Whisper)
             Agent 2: Summarization  (Llama 3.2 / Qwen)
             Agent 3+4: Extraction   (Mistral)
             Save everything to DB via SQLModel
"""

from sqlmodel import Session, select
from app.models.db_models import Meeting, ActionItem
from app.models.database import engine
from app.agents.transcription import transcribe
from app.agents.summarizer import summarize
from app.agents.action_extractor import extract_and_prioritize


async def run_pipeline(meeting_id: int, audio_path: str | None = None) -> dict:
    """
    Runs the full agent pipeline for a meeting.

    Args:
        meeting_id : DB id of the meeting (already created before this runs)
        audio_path : path to audio file, or None if input was text

    Returns:
        dict with summary + action_items
    """
    with Session(engine) as session:

        # Fetch the meeting from DB
        meeting = session.get(Meeting, meeting_id)
        if not meeting:
            raise ValueError(f"Meeting {meeting_id} not found in DB")

        # Mark as processing so UI can show a spinner
        meeting.status = "processing"
        session.add(meeting)
        session.commit()

        try:

            # ── Step 1: Transcription ─────────────────────────
            if audio_path:
                # Audio input → run Whisper
                print(f"[Pipeline] Step 1/3 → Transcription")
                transcript = await transcribe(audio_path, meeting_id)
                meeting.transcript = transcript
            else:
                # Text input → transcript already saved in meeting.transcript
                transcript = meeting.transcript or ""
                print(f"[Pipeline] Step 1/3 → Skipped (text input, {len(transcript)} chars)")

            # ── Step 2: Summarization ─────────────────────────
            print(f"[Pipeline] Step 2/3 → Summarization")
            summary = await summarize(transcript, meeting_id)
            meeting.summary = summary

            # ── Step 3+4: Extraction + Prioritization ─────────
            print(f"[Pipeline] Step 3/3 → Action Extraction")
            action_items = await extract_and_prioritize(
                transcript=transcript,
                summary=summary,
                meeting_id=meeting_id,
            )

            # ── Persist action items to DB ────────────────────
            # Each extracted dict becomes one ActionItem row
            for item in action_items:
                db_item = ActionItem(
                    meeting_id=meeting_id,
                    task=item["task"],
                    owner=item.get("owner"),
                    priority=item.get("priority", "Medium"),
                    deadline=item.get("deadline"),
                )
                session.add(db_item)

            # Mark meeting as done
            meeting.status = "done"
            session.add(meeting)
            session.commit()

            print(f"[Pipeline] Done — {len(action_items)} actions extracted")

            return {
                "meeting_id": meeting_id,
                "summary": summary,
                "action_items": action_items,
                "total_actions": len(action_items),
            }

        except Exception as e:
            # If anything fails, mark meeting as error
            # so the UI shows a clear error state instead of hanging
            meeting.status = "error"
            session.add(meeting)
            session.commit()
            print(f"[Pipeline] ❌ Error: {e}")
            raise