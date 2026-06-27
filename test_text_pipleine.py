import asyncio
from pathlib import Path

from sqlmodel import Session

from app.models.database import create_db_and_tables, engine
from app.models.db_models import Meeting
from app.agents.pipeline import run_pipeline
# test_text_pipeline.py — add near the top, before anything else
from app.config import settings
settings.ensure_dirs()

async def main():

    # --------------------------------------------------
    # Step 1: Create DB & Tables
    # --------------------------------------------------
    create_db_and_tables()

    print("✅ Database and tables are ready.\n")

    # --------------------------------------------------
    # Step 2: Read meeting notes from file
    # --------------------------------------------------
    notes = Path("data/meeting_notes.txt").read_text(
        encoding="utf-8"
    )

    # --------------------------------------------------
    # Step 3: Insert Meeting
    # --------------------------------------------------
    with Session(engine) as session:

        meeting = Meeting(
            title="Sprint Planning Meeting",
            original_filename="meeting_notes.txt",
            input_type="text",
            file_path="data/meeting_notes.txt",
            transcript=notes,
        )

        session.add(meeting)
        session.commit()
        session.refresh(meeting)

        meeting_id = meeting.id

        print("✅ Meeting inserted successfully.")
        print(f"Meeting ID : {meeting_id}\n")

    # --------------------------------------------------
    # Step 4: Run Pipeline
    # --------------------------------------------------
    print("=" * 70)
    print("Running AI Pipeline...")
    print("=" * 70)

    result = await run_pipeline(
        meeting_id=meeting_id,
        audio_path=None,      # Text input → Skip transcription
    )

    # --------------------------------------------------
    # Step 5: Print Final Result
    # --------------------------------------------------
    print("\n")
    print("=" * 70)
    print("FINAL RESULT")
    print("=" * 70)

    print(f"Meeting ID    : {result['meeting_id']}")
    print(f"Total Actions : {result['total_actions']}")

    print("\nSUMMARY\n")
    print(result["summary"])

    print("\nACTION ITEMS\n")

    for i, item in enumerate(result["action_items"], start=1):
        print(f"Action {i}")
        print(f"Task      : {item['task']}")
        print(f"Owner     : {item['owner']}")
        print(f"Priority  : {item['priority']}")
        print(f"Deadline  : {item['deadline']}")
        print("-" * 40)


if __name__ == "__main__":
    asyncio.run(main())