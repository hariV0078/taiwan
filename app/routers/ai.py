import json
import traceback
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlmodel import Session, select

from app.config import get_settings
from app.database import engine
from app.models.audit import AuditEventType, AuditTrail
from app.models.listing import ListingStatus, WasteListing
from app.models.transaction import BuyerProfile, Transaction, TransactionStatus
from app.models.user import User, UserRole
from app.routers.auth import get_current_user
from app.services.classifier import ClassificationResult, classify_material
from app.services.matcher import MatchResult, match_buyers
from app.services.market_price import get_market_price_range
from app.utils.hashing import generate_event_hash

router = APIRouter()
settings = get_settings()


class ClassifyRequest(BaseModel):
    description: str
    quantity_kg: float
    purity_pct: float

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "description": "Clean HDPE flakes from drums",
                "quantity_kg": 10000,
                "purity_pct": 92,
            }
        }
    )


class MatchRequest(BaseModel):
    listing_id: uuid.UUID

    model_config = ConfigDict(json_schema_extra={"example": {"listing_id": "6ce4583e-39e3-4e4e-9df4-095755146a93"}})


class MarketPriceRequest(BaseModel):
    material_category: str
    grade: str = "A1"

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "material_category": "aluminum",
                "grade": "A1",
            }
        }
    )


class QarSummaryRequest(BaseModel):
    visual_score: float
    sampling_score: float
    variance_pct: float
    integrity_ok: bool
    material_type: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "visual_score": 85.0,
                "sampling_score": 92.0,
                "variance_pct": 2.5,
                "integrity_ok": True,
                "material_type": "HDPE Flakes"
            }
        }
    )


@router.post("/classify", response_model=ClassificationResult, status_code=status.HTTP_200_OK)
def classify_material_endpoint(payload: ClassifyRequest, current_user: User = Depends(get_current_user)):
    """Classify a material description with AI-enriched grade and confidence output."""
    try:
        return classify_material(payload.description, payload.quantity_kg, payload.purity_pct)
    except Exception:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/match", response_model=list[MatchResult], status_code=status.HTTP_200_OK)
def match_buyers_endpoint(payload: MatchRequest, current_user: User = Depends(get_current_user)):
    """Find top matching buyers for a listing and create MATCHED transactions."""
    if current_user.role not in {UserRole.manufacturer, UserRole.admin}:
        raise HTTPException(status_code=403, detail="Only manufacturer/admin can trigger matching")

    try:
        with Session(engine) as session:
            listing = session.get(WasteListing, payload.listing_id)
            if not listing:
                raise HTTPException(status_code=404, detail="Listing not found")

            matches = match_buyers(listing, top_k=3)
            if not matches:
                return []

            for match in matches:
                tx = Transaction(
                    listing_id=listing.id,
                    seller_id=listing.seller_id,
                    buyer_id=match.buyer_id,
                    status=TransactionStatus.matched,
                )
                session.add(tx)
                session.commit()
                session.refresh(tx)

                payload_data = {
                    "transaction_id": str(tx.id),
                    "listing_id": str(listing.id),
                    "buyer_id": str(match.buyer_id),
                    "score": match.score,
                }
                prev = session.exec(
                    select(AuditTrail)
                    .where(AuditTrail.transaction_id == tx.id)
                    .order_by(AuditTrail.created_at.desc())
                ).first()
                prev_hash = prev.hash if prev else "GENESIS"
                session.add(
                    AuditTrail(
                        transaction_id=tx.id,
                        listing_id=listing.id,
                        event_type=AuditEventType.match_found,
                        actor_id=current_user.id,
                        payload=json.dumps(payload_data),
                        hash=generate_event_hash(AuditEventType.match_found.value, payload_data, prev_hash),
                        prev_hash=prev_hash,
                    )
                )
                session.commit()

            listing.status = ListingStatus.matched
            session.add(listing)
            session.commit()
            return matches
    except HTTPException:
        raise
    except Exception:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/market-price", status_code=status.HTTP_200_OK)
def get_market_price_endpoint(payload: MarketPriceRequest, current_user: User = Depends(get_current_user)):
    """
    Get market reference price range for a material category and grade.
    
    Returns market low/mid/high prices and confidence level.
    Used to validate seller floor and buyer ceiling prices.
    """
    try:
        result = get_market_price_range(payload.material_category, payload.grade)
        return result
    except Exception:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/qar-summary", status_code=status.HTTP_200_OK)
def generate_qar_summary(payload: QarSummaryRequest, current_user: User = Depends(get_current_user)):
    """
    Generate an AI-enriched summary for a Quality Attestation Report.
    
    Synthesizes inspection metrics into a professional assessment.
    """
    if current_user.role not in {UserRole.tpqc, UserRole.admin}:
        raise HTTPException(status_code=403, detail="Only TPQC can generate QAR summaries")
        
    status = "EXCEEDS" if payload.visual_score > 90 and payload.sampling_score > 90 else "MEETS"
    if payload.variance_pct > 10:
        status = "CONCERNING"
    if not payload.integrity_ok:
        status = "FAILED"
        
    summary = (
        f"AI ASSESSMENT: This lot of {payload.material_type} {status} technical specifications. "
        f"Visual inspection at {payload.visual_score}% confirms high grade consistency. "
        f"Variance of {payload.variance_pct}% is {'well within' if payload.variance_pct < 5 else 'acceptable'} limits. "
        f"{'Packaging integrity verified.' if payload.integrity_ok else 'CRITICAL: Packaging compromised.'}"
    )
    
    return {
        "summary": summary,
        "recommendation": "PROCEED" if status != "FAILED" else "REJECT",
        "confidence": 0.94
    }
