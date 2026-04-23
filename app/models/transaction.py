import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel


class TransactionStatus(str, Enum):
    matched = "MATCHED"
    buyer_interested = "BUYER_INTERESTED"  # NEW: Buyer confirms interest in match
    price_proposed = "PRICE_PROPOSED"  # NEW: ZOPA calculated, prices sent to both
    price_countered = "PRICE_COUNTERED"  # NEW: One or both parties counter-offered
    agreed = "AGREED"
    locked = "LOCKED"
    inspecting = "INSPECTING"  # NEW: Inspector assigned and working (renamed from implicit state)
    verified = "VERIFIED"
    released = "RELEASED"
    disputed = "DISPUTED"
    failed = "FAILED"


class Transaction(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    listing_id: uuid.UUID = Field(foreign_key="wastelisting.id", index=True)
    seller_id: uuid.UUID = Field(foreign_key="user.id")
    buyer_id: uuid.UUID = Field(foreign_key="user.id")
    agreed_price_per_kg: Optional[float] = None
    total_value: Optional[float] = None
    platform_fee: Optional[float] = None
    seller_payout: Optional[float] = None
    status: TransactionStatus = TransactionStatus.matched
    negotiation_rounds: int = 0
    negotiation_transcript: Optional[str] = None
    escrow_hash: Optional[str] = None
    qar_hash: Optional[str] = None
    qar_notes: Optional[str] = None
    dpp_path: Optional[str] = None
    co2_saved_kg: Optional[float] = None
    matched_at: datetime = Field(default_factory=datetime.utcnow)
    
    # NEW: Human-in-the-loop fields
    buyer_confirmed_interest_at: Optional[datetime] = None  # When buyer confirmed interest
    initial_proposed_price: Optional[float] = None  # What ZOPA calculated
    counter_offer_from_seller: Optional[float] = None  # Seller's one counter-offer
    counter_offer_from_buyer: Optional[float] = None  # Buyer's one counter-offer
    counter_offer_expires_at: Optional[datetime] = None  # Deadline for counter-offer
    seller_accepted_price_at: Optional[datetime] = None  # When seller accepted final price
    buyer_accepted_price_at: Optional[datetime] = None  # When buyer accepted final price
    
    locked_at: Optional[datetime] = None
    verified_at: Optional[datetime] = None
    released_at: Optional[datetime] = None


class NegotiationRound(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    transaction_id: uuid.UUID = Field(foreign_key="transaction.id", index=True)
    round_number: int
    role: str
    offered_price: float
    reasoning: str
    accepted: bool
    created_at: datetime = Field(default_factory=datetime.utcnow)


class BuyerProfile(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    buyer_id: uuid.UUID = Field(foreign_key="user.id", unique=True)
    material_needs: str
    accepted_grades: str
    accepted_countries: str
    max_price_per_kg: float
    min_quantity_kg: float
    max_quantity_kg: float
    chroma_doc_id: Optional[str] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)
