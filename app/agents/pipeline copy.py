from sqlmodel import Session
from app.agents.action_extractor import extract_and_prioritize
from app.agents.summarizer import summarize
from app.agents.transcription import transcribe
from app.models.database import engine
from app.models.db_models import Meeting, ActionItem

async def run_pipeline(meeting_id: int, audio_path: str | None = None) -> dict:
    with Session(engine) as session:
        meeting = session.get(Meeting, meeting_id)
        if not meeting:
            raise ValueError(f"Meeting {meeting_id} not found in DB")


        meeting.status = "processing"
        session.add(meeting)
        session.commit()

        try:
            if audio_path:
                print(f"[Pipeline] Step 1/3 → Transcription")
                transcript = await transcribe(audio_path, meeting_id)
                meeting.transcript = transcript
            else:
                transcript = meeting.transcript or ""
                print(f"[Pipeline] Step 1/3 → Skipped (text input, {len(transcript)} chars)")
                

            print(f"[Pipeline] Step 2/3 → Summarization")
            summary = await summarize(transcript, meeting_id)
            meeting.summary = summary

            print(f"[Pipeline] Step 3/3 → Action Extraction")
            action_items = await extract_and_prioritize(
                transcript=transcript,
                summary=summary,
                meeting_id=meeting_id
            )

            for item in action_items:
                db_item = ActionItem(
                    meeting_id=meeting_id,
                    task = item["task"],
                    owner = item.get("owner"),
                    priority=item.get("priority", "Medium"),
                    deadline=item.get("deadline")
                )
                session.add(db_item)
            
            meeting.status="done"
            session.add(meeting)
            session.commit()
            print(f"[Pipeline] ✅ Done — {len(action_items)} actions extracted")

            return {
                "meeting_id": meeting_id,
                "summary": summary,
                "action_items": action_items,
                "total_actions": len(action_items)
            }

            
        except Exception as e:
            meeting.status="error"
            session.add(meeting)
            session.commit()
            print(f"[Pipeline] ❌ Error: {e}")
            raise
