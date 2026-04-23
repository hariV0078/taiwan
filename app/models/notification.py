import uuid
from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class Notification(SQLModel, table=True):
    """In-app notification for users on transaction events."""
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id", index=True)
    transaction_id: Optional[uuid.UUID] = Field(default=None, foreign_key="transaction.id", index=True)
    message: str  # e.g., "Match found! IndoPoly Recyclers wants your aluminum"
    notification_type: str  # e.g., "MATCH_FOUND", "PRICE_PROPOSED", "BUYER_CONFIRMED", etc.
    is_read: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    read_at: Optional[datetime] = None


# Pydantic models for API responses
class NotificationOut(SQLModel):
    id: uuid.UUID
    user_id: uuid.UUID
    transaction_id: Optional[uuid.UUID]
    message: str
    notification_type: str
    is_read: bool
    created_at: datetime
    read_at: Optional[datetime]
