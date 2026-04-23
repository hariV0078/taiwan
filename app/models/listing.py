import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel


class ListingStatus(str, Enum):
    active = "active"
    matched = "matched"
    negotiating = "negotiating"
    sold = "sold"
    blocked = "blocked"
    expired = "expired"


class MaterialGrade(str, Enum):
    A1 = "A1"
    A2 = "A2"
    B1 = "B1"
    B2 = "B2"
    C = "C"


class WasteListing(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    seller_id: uuid.UUID = Field(foreign_key="user.id", index=True)
    material_type: str
    material_category: str
    grade: Optional[MaterialGrade] = None
    quantity_kg: float
    purity_pct: float
    location_city: str
    location_country: str
    ask_price_per_kg: float
    confidence_score: Optional[float] = None
    needs_tpqc: bool = False
    is_blocked: bool = False
    block_reason: Optional[str] = None
    status: ListingStatus = ListingStatus.active
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
