import asyncio
from pathlib import Path

from sqlmodel import Session

from app.models.database import create_db_and_tables, engine
from app.models.db_models import Meeting
from app.agents.pipeline import run_pipeline
from app.config import settings

settings.ensure_dirs()


async def main():

    # --------------------------------------------------
    # Step 1: Create DB & Tables
    # --------------------------------------------------
    create_db_and_tables()

    print("✅ Database and tables are ready.\n")

    # --------------------------------------------------
    # Step 2: Audio file path
    # --------------------------------------------------
    audio_path = "data/team_meeting.mp4"

    if not Path(audio_path).exists():
        raise FileNotFoundError(audio_path)

    # --------------------------------------------------
    # Step 3: Insert Meeting
    # --------------------------------------------------
    with Session(engine) as session:

        meeting = Meeting(
            title="Audio Meeting Test",
            original_filename="team_meeting.mp4",
            input_type="audio",
            file_path=audio_path,
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
    result = await run_pipeline(
        meeting_id=meeting_id,
        audio_path=audio_path,
    )

    # --------------------------------------------------
    # Step 5: Print Final Result
    # --------------------------------------------------
    print("\n" + "=" * 70)
    print("FINAL RESULT")
    print("=" * 70)

    print(f"Meeting ID    : {result['meeting_id']}")
    print(f"Total Actions : {result['total_actions']}")

    print("\nSUMMARY\n")
    print(result["summary"])

    print("\nACTION ITEMS\n")

    for item in result["action_items"]:
        print(item)


if __name__ == "__main__":
    asyncio.run(main())