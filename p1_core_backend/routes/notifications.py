from fastapi import APIRouter, HTTPException

from p1_core_backend.db import store
from shared.schemas import Notification


router = APIRouter()


@router.get("/notifications/{user_id}", response_model=list[Notification])
def get_notifications(user_id: str, unread: bool = False) -> list[Notification]:
    notices = store.list_notifications(user_id)
    return [notice for notice in notices if not notice.read] if unread else notices


@router.post("/notifications/{notification_id}/read", response_model=Notification)
def mark_read(notification_id: str) -> Notification:
    notice = store.get_notification(notification_id)
    if notice is None:
        raise HTTPException(status_code=404, detail="Notification not found")

    updated = notice.model_copy(update={"read": True})
    store.save_notification(updated)
    return updated