"""
Notifications Router
Manages in-app notifications for users.
"""

import traceback
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlmodel import Session, select

from app.database import engine
from app.models.notification import Notification
from app.models.user import User
from app.routers.auth import get_current_user

router = APIRouter()


class NotificationResponse(BaseModel):
    """Response with notification details."""
    id: uuid.UUID
    user_id: uuid.UUID
    transaction_id: uuid.UUID | None
    message: str
    notification_type: str
    is_read: bool
    created_at: datetime
    read_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class MarkAsReadRequest(BaseModel):
    """Request to mark notification as read."""
    pass


@router.get("/", response_model=list[NotificationResponse], status_code=status.HTTP_200_OK)
def get_notifications(
    unread_only: bool = False,
    limit: int = 50,
    skip: int = 0,
    current_user: User = Depends(get_current_user)
):
    """
    Get notifications for current user.
    
    Args:
        unread_only: If true, only return unread notifications
        limit: Maximum notifications to return (default 50)
        skip: Number of notifications to skip (pagination)
    """
    try:
        with Session(engine) as session:
            query = select(Notification).where(Notification.user_id == current_user.id)
            
            if unread_only:
                query = query.where(Notification.is_read == False)
            
            query = query.order_by(Notification.created_at.desc()).offset(skip).limit(limit)
            
            result = session.exec(query)
            notifications = result.all()
            
            return notifications
    except Exception:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal server error")


@router.patch("/{notification_id}/read", response_model=NotificationResponse, status_code=status.HTTP_200_OK)
def mark_notification_as_read(
    notification_id: uuid.UUID,
    current_user: User = Depends(get_current_user)
):
    """
    Mark a notification as read.
    
    Only the recipient user can mark their own notifications as read.
    """
    try:
        with Session(engine) as session:
            notification = session.get(Notification, notification_id)
            
            if not notification:
                raise HTTPException(status_code=404, detail="Notification not found")
            
            if notification.user_id != current_user.id:
                raise HTTPException(status_code=403, detail="Can only mark your own notifications as read")
            
            notification.is_read = True
            notification.read_at = datetime.utcnow()
            
            session.add(notification)
            session.commit()
            session.refresh(notification)
            
            return notification
    except HTTPException:
        raise
    except Exception:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/mark-all-read", response_model=dict, status_code=status.HTTP_200_OK)
def mark_all_notifications_read(
    current_user: User = Depends(get_current_user)
):
    """
    Mark all notifications for current user as read.
    
    Returns count of notifications marked as read.
    """
    try:
        with Session(engine) as session:
            result = session.exec(
                select(Notification).where(
                    Notification.user_id == current_user.id,
                    Notification.is_read == False
                )
            )
            notifications = result.all()
            
            count = 0
            for notification in notifications:
                notification.is_read = True
                notification.read_at = datetime.utcnow()
                session.add(notification)
                count += 1
            
            session.commit()
            
            return {"marked_as_read": count}
    except Exception:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal server error")
