"""
Notifier Service
Manages in-app notifications (database-backed, no email/SMS).

Notifications are created in response to transaction state changes and other events.
Users poll GET /notifications/ on page load to retrieve unread notifications.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID


async def create_notification(
    session,
    user_id: UUID,
    message: str,
    notification_type: str,
    transaction_id: Optional[UUID] = None
) -> dict:
    """
    Create a new notification for a user.
    
    Args:
        session: SQLModel async session
        user_id: ID of user to notify
        message: Notification message
        notification_type: Type of notification (e.g., "MATCH_FOUND", "PRICE_PROPOSED")
        transaction_id: Optional transaction ID if related to a transaction
    
    Returns:
        Notification data as dict
    """
    from app.models.notification import Notification
    
    notification = Notification(
        user_id=user_id,
        message=message,
        notification_type=notification_type,
        transaction_id=transaction_id,
        is_read=False
    )
    session.add(notification)
    await session.commit()
    await session.refresh(notification)
    
    return {
        "id": str(notification.id),
        "user_id": str(notification.user_id),
        "message": notification.message,
        "notification_type": notification.notification_type,
        "transaction_id": str(notification.transaction_id) if notification.transaction_id else None,
        "is_read": notification.is_read,
        "created_at": notification.created_at.isoformat()
    }


async def get_user_notifications(
    session,
    user_id: UUID,
    unread_only: bool = False,
    limit: int = 50,
    skip: int = 0
) -> list[dict]:
    """
    Get notifications for a user.
    
    Args:
        session: SQLModel async session
        user_id: ID of user
        unread_only: If True, only return unread notifications
        limit: Max number of notifications to return
        skip: Number of notifications to skip (pagination)
    
    Returns:
        List of notification dicts
    """
    from app.models.notification import Notification
    from sqlmodel import select
    
    query = select(Notification).where(Notification.user_id == user_id)
    
    if unread_only:
        query = query.where(Notification.is_read == False)
    
    query = query.order_by(Notification.created_at.desc()).offset(skip).limit(limit)
    
    result = await session.exec(query)
    notifications = result.all()
    
    return [
        {
            "id": str(n.id),
            "user_id": str(n.user_id),
            "message": n.message,
            "notification_type": n.notification_type,
            "transaction_id": str(n.transaction_id) if n.transaction_id else None,
            "is_read": n.is_read,
            "created_at": n.created_at.isoformat(),
            "read_at": n.read_at.isoformat() if n.read_at else None
        }
        for n in notifications
    ]


async def mark_notification_as_read(
    session,
    notification_id: UUID
) -> dict:
    """
    Mark a notification as read.
    
    Args:
        session: SQLModel async session
        notification_id: ID of notification to mark as read
    
    Returns:
        Updated notification data
    """
    from app.models.notification import Notification
    from sqlmodel import select
    
    result = await session.exec(select(Notification).where(Notification.id == notification_id))
    notification = result.first()
    
    if not notification:
        raise ValueError(f"Notification {notification_id} not found")
    
    notification.is_read = True
    notification.read_at = datetime.utcnow()
    session.add(notification)
    await session.commit()
    await session.refresh(notification)
    
    return {
        "id": str(notification.id),
        "user_id": str(notification.user_id),
        "message": notification.message,
        "notification_type": notification.notification_type,
        "transaction_id": str(notification.transaction_id) if notification.transaction_id else None,
        "is_read": notification.is_read,
        "created_at": notification.created_at.isoformat(),
        "read_at": notification.read_at.isoformat() if notification.read_at else None
    }


async def mark_all_as_read(
    session,
    user_id: UUID
) -> int:
    """
    Mark all notifications for a user as read.
    
    Args:
        session: SQLModel async session
        user_id: ID of user
    
    Returns:
        Number of notifications updated
    """
    from app.models.notification import Notification
    from sqlmodel import select
    
    result = await session.exec(
        select(Notification).where(
            Notification.user_id == user_id,
            Notification.is_read == False
        )
    )
    notifications = result.all()
    
    for notification in notifications:
        notification.is_read = True
        notification.read_at = datetime.utcnow()
        session.add(notification)
    
    await session.commit()
    return len(notifications)
