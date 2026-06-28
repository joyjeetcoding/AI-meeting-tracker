from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select

from app.models.db_models import Meeting, ActionItem, MeetingOut, ActionItemOut, ActionItemUpdate
from app.models.database import get_session


router = APIRouter(tags=["meetings"])


@router.get("/get-summary/{meeting_id}")
async def get_summary(
    meeting_id: int,
    session: Session = Depends(get_session),
):
    meeting = session.get(Meeting, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail=f"Meeting {meeting_id} not found")

    items = session.exec(
        select(ActionItem).where(ActionItem.meeting_id == meeting_id)
    ).all()

    return {
        "id": meeting.id,
        "title": meeting.title,
        "summary": meeting.summary,
        "status": meeting.status,
        "created_at": meeting.created_at,
        "action_items": [
            {
                "id": i.id,
                "task": i.task,
                "owner": i.owner,
                "priority": i.priority,
                "deadline": i.deadline,
                "status": i.status,
            }
            for i in items
        ],
    }


@router.get("/extract-actions/{meeting_id}", response_model=list[ActionItemOut])
async def extract_actions(
    meeting_id: int,
    session: Session = Depends(get_session),
):
    meeting = session.get(Meeting, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail=f"Meeting {meeting_id} not found")

    items = session.exec(
        select(ActionItem).where(ActionItem.meeting_id == meeting_id)
    ).all()
    return items


@router.get("/meetings")
async def list_meetings(session: Session = Depends(get_session)):
    meetings = session.exec(select(Meeting)).all()
    result = []
    for m in meetings:
        items = session.exec(
            select(ActionItem).where(ActionItem.meeting_id == m.id)
        ).all()
        result.append({
            "id": m.id,
            "title": m.title,
            "status": m.status,
            "created_at": m.created_at,
            "action_count": len(items),
        })
    return result


@router.get("/meetings/{meeting_id}/status")
async def get_status(
    meeting_id: int,
    session: Session = Depends(get_session),
):
    meeting = session.get(Meeting, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail=f"Meeting {meeting_id} not found")
    return {"meeting_id": meeting_id, "status": meeting.status}


@router.patch("/update-action/{action_id}", response_model=ActionItemOut)
async def update_action(
    action_id: int,
    updates: ActionItemUpdate,
    session: Session = Depends(get_session),
):
    item = session.get(ActionItem, action_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"Action item {action_id} not found")

    update_data = updates.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(item, key, value)

    session.add(item)
    session.commit()
    session.refresh(item)
    return item