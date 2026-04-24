import json
import traceback
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlmodel import Session, select

from app.database import engine
from app.models.audit import AuditEventType, AuditTrail
from app.models.listing import ListingStatus, MaterialGrade, WasteListing
from app.models.user import User, UserRole
from app.routers.auth import get_current_user
from app.services.classifier import classify_material
from app.utils.hashing import generate_event_hash

router = APIRouter()


class ListingCreateRequest(BaseModel):
    material_type: str
    quantity_kg: float
    purity_pct: float
    location_city: str
    location_country: str
    ask_price_per_kg: float
    description: Optional[str] = None
    expires_at: Optional[datetime] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "material_type": "HDPE plastic",
                "quantity_kg": 12000,
                "purity_pct": 88,
                "location_city": "Mumbai",
                "location_country": "IN",
                "ask_price_per_kg": 0.65,
                "description": "Clean post-industrial HDPE flakes",
            }
        }
    )


class ListingStatusPatchRequest(BaseModel):
    status: ListingStatus

    model_config = ConfigDict(json_schema_extra={"example": {"status": "expired"}})


class ListingOut(BaseModel):
    id: uuid.UUID
    seller_id: uuid.UUID
    material_type: str
    material_category: str
    grade: Optional[MaterialGrade]
    quantity_kg: float
    purity_pct: float
    location_city: str
    location_country: str
    ask_price_per_kg: float
    confidence_score: Optional[float]
    needs_tpqc: bool
    is_blocked: bool
    block_reason: Optional[str]
    status: ListingStatus
    description: Optional[str]
    created_at: datetime
    expires_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)



def _latest_listing_hash(listing_id: uuid.UUID, session: Session) -> str:
    row = session.exec(
        select(AuditTrail)
        .where(AuditTrail.listing_id == listing_id)
        .order_by(AuditTrail.created_at.desc())
    ).first()
    return row.hash if row else "GENESIS"


@router.post("/", response_model=ListingOut, status_code=status.HTTP_201_CREATED)
def create_listing(payload: ListingCreateRequest, current_user: User = Depends(get_current_user)):
    """Create a new waste listing and auto-classify material attributes."""
    if current_user.role != UserRole.manufacturer:
        raise HTTPException(status_code=403, detail="Only manufacturers can create listings")

    try:
        classification = classify_material(
            description=payload.description or payload.material_type,
            quantity_kg=payload.quantity_kg,
            purity_pct=payload.purity_pct,
        )

        with Session(engine) as session:
            listing = WasteListing(
                seller_id=current_user.id,
                material_type=payload.material_type,
                material_category=classification.material_category,
                grade=classification.grade,
                quantity_kg=payload.quantity_kg,
                purity_pct=payload.purity_pct,
                location_city=payload.location_city,
                location_country=payload.location_country,
                ask_price_per_kg=payload.ask_price_per_kg,
                confidence_score=classification.confidence,
                needs_tpqc=classification.needs_tpqc,
                is_blocked=classification.is_blocked,
                block_reason=classification.block_reason,
                status=ListingStatus.blocked if classification.is_blocked else ListingStatus.active,
                description=payload.description,
                expires_at=payload.expires_at,
            )
            session.add(listing)
            session.commit()
            session.refresh(listing)

            payload_data = {
                "listing_id": str(listing.id),
                "seller_id": str(current_user.id),
                "status": listing.status.value,
                "grade": listing.grade.value if listing.grade else None,
            }
            prev_hash = _latest_listing_hash(listing.id, session)
            event_type = (
                AuditEventType.listing_blocked if listing.is_blocked else AuditEventType.listing_created
            )
            event_hash = generate_event_hash(event_type.value, payload_data, prev_hash)
            session.add(
                AuditTrail(
                    listing_id=listing.id,
                    event_type=event_type,
                    actor_id=current_user.id,
                    payload=json.dumps(payload_data),
                    hash=event_hash,
                    prev_hash=prev_hash,
                )
            )
            session.commit()
            return ListingOut.model_validate(listing)
    except HTTPException:
        raise
    except Exception:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/", response_model=list[ListingOut], status_code=status.HTTP_200_OK)
def list_active_listings(skip: int = 0, limit: int = 20):
    """List active marketplace listings with pagination."""
    try:
        with Session(engine) as session:
            listings = session.exec(
                select(WasteListing)
                .where(WasteListing.status == ListingStatus.active)
                .offset(skip)
                .limit(limit)
            ).all()
            return [ListingOut.model_validate(x) for x in listings]
    except Exception:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/my", response_model=list[ListingOut], status_code=status.HTTP_200_OK)
def my_listings(current_user: User = Depends(get_current_user)):
    """Return listings owned by the current user."""
    try:
        with Session(engine) as session:
            listings = session.exec(
                select(WasteListing).where(WasteListing.seller_id == current_user.id)
            ).all()
            return [ListingOut.model_validate(x) for x in listings]
    except Exception:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{listing_id}", response_model=ListingOut, status_code=status.HTTP_200_OK)
def get_listing(listing_id: uuid.UUID):
    """Get a single listing by its ID."""
    try:
        with Session(engine) as session:
            listing = session.get(WasteListing, listing_id)
            if not listing:
                raise HTTPException(status_code=404, detail="Listing not found")
            return ListingOut.model_validate(listing)
    except HTTPException:
        raise
    except Exception:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal server error")


@router.patch("/{listing_id}/status", response_model=ListingOut, status_code=status.HTTP_200_OK)
def update_listing_status(
    listing_id: uuid.UUID,
    payload: ListingStatusPatchRequest,
    current_user: User = Depends(get_current_user),
):
    """Update listing status by the owner manufacturer or admin."""
    try:
        with Session(engine) as session:
            listing = session.get(WasteListing, listing_id)
            if not listing:
                raise HTTPException(status_code=404, detail="Listing not found")
            if current_user.role not in {UserRole.admin, UserRole.manufacturer}:
                raise HTTPException(status_code=403, detail="Forbidden")
            if current_user.role == UserRole.manufacturer and listing.seller_id != current_user.id:
                raise HTTPException(status_code=403, detail="Not your listing")
            listing.status = payload.status
            session.add(listing)
            session.commit()
            session.refresh(listing)
            return ListingOut.model_validate(listing)
    except HTTPException:
        raise
    except Exception:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{listing_id}", response_model=ListingOut, status_code=status.HTTP_200_OK)
def soft_delete_listing(listing_id: uuid.UUID, current_user: User = Depends(get_current_user)):
    """Soft delete a listing by marking it as expired."""
    try:
        with Session(engine) as session:
            listing = session.get(WasteListing, listing_id)
            if not listing:
                raise HTTPException(status_code=404, detail="Listing not found")
            if current_user.role not in {UserRole.admin, UserRole.manufacturer}:
                raise HTTPException(status_code=403, detail="Forbidden")
            if current_user.role == UserRole.manufacturer and listing.seller_id != current_user.id:
                raise HTTPException(status_code=403, detail="Not your listing")
            listing.status = ListingStatus.expired
            session.add(listing)
            session.commit()
            session.refresh(listing)
            return ListingOut.model_validate(listing)
    except HTTPException:
        raise
    except Exception:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal server error")
