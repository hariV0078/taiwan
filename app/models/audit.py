import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel


class AuditEventType(str, Enum):
    listing_created = "LISTING_CREATED"
    listing_blocked = "LISTING_BLOCKED"
    match_found = "MATCH_FOUND"
    negotiation_start = "NEGOTIATION_START"
    negotiation_round = "NEGOTIATION_ROUND"
    deal_agreed = "DEAL_AGREED"
    escrow_locked = "ESCROW_LOCKED"
    tpqc_verified = "TPQC_VERIFIED"
    tpqc_rejected = "TPQC_REJECTED"
    escrow_released = "ESCROW_RELEASED"
    dpp_generated = "DPP_GENERATED"


class AuditTrail(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    transaction_id: Optional[uuid.UUID] = Field(default=None, foreign_key="transaction.id", index=True)
    listing_id: Optional[uuid.UUID] = Field(default=None, foreign_key="wastelisting.id")
    event_type: AuditEventType
    actor_id: Optional[uuid.UUID] = None
    payload: str
    hash: str
    prev_hash: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
