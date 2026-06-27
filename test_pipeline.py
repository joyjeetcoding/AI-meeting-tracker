from sqlmodel import Session

from app.models.database import create_db_and_tables, engine
from app.models.db_models import Meeting
from pathlib import Path

create_db_and_tables()

print("✅ Database and tables are ready.\n")

notes = Path("data/meeting_notes.txt").read_text(encoding="utf-8")

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

    print("✅ Meeting inserted successfully.\n")

    print("Meeting Details")
    print("-" * 50)
    print(f"Meeting ID : {meeting.id}")
    print(f"Title      : {meeting.title}")
    print(f"Type       : {meeting.input_type}")
    print(f"Status     : {meeting.status}")

    print("\nTranscript")
    print("-" * 50)
    print(meeting.transcript)
