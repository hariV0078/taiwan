import os
import traceback
import uuid
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict
from sqlmodel import Session, select

from app.config import get_settings
from app.database import engine
from app.models.audit import AuditTrail
from app.models.listing import WasteListing
from app.models.notification import Notification
from app.models.transaction import BuyerProfile, Transaction, TransactionStatus
from app.models.user import User, UserRole
from app.routers.auth import get_current_user
from app.services.escrow import EscrowResult, get_audit_chain, lock_escrow
from app.services.market_price import get_market_price_range
from app.services.zopa import calculate_zopa, check_counter_offer_zopa
from app.utils.hashing import generate_event_hash
from app.models.audit import AuditEventType
import json

router = APIRouter()


class TransactionOut(BaseModel):
    id: uuid.UUID
    listing_id: uuid.UUID
    seller_id: uuid.UUID
    buyer_id: uuid.UUID
    agreed_price_per_kg: Optional[float]
    total_value: Optional[float]
    platform_fee: Optional[float]
    seller_payout: Optional[float]
    status: TransactionStatus
    negotiation_rounds: int
    negotiation_transcript: Optional[str]
    escrow_hash: Optional[str]
    qar_hash: Optional[str]
    qar_notes: Optional[str]
    dpp_path: Optional[str]
    co2_saved_kg: Optional[float]
    seller_name: Optional[str] = None
    material_type: Optional[str] = None
    material_grade: Optional[str] = None
    purity_pct: Optional[float] = None
    location_city: Optional[str] = None
    location_country: Optional[str] = None
    quantity_kg: Optional[float] = None
    created_at: Optional[datetime] = None
    confidence_score: Optional[float] = None
    matched_at: datetime
    buyer_confirmed_interest_at: Optional[datetime]
    initial_proposed_price: Optional[float]
    counter_offer_from_seller: Optional[float]
    counter_offer_from_buyer: Optional[float]
    counter_offer_expires_at: Optional[datetime]
    seller_accepted_price_at: Optional[datetime]
    buyer_accepted_price_at: Optional[datetime]
    locked_at: Optional[datetime]
    verified_at: Optional[datetime]
    released_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class AuditOut(BaseModel):
    id: uuid.UUID
    transaction_id: Optional[uuid.UUID]
    listing_id: Optional[uuid.UUID]
    event_type: str
    actor_id: Optional[uuid.UUID]
    payload: str
    hash: str
    prev_hash: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


@router.get("/", response_model=list[TransactionOut], status_code=status.HTTP_200_OK)
def list_transactions(current_user: User = Depends(get_current_user)):
    """List transactions filtered by role visibility rules."""
    try:
        with Session(engine) as session:
            if current_user.role == UserRole.manufacturer:
                query = select(Transaction).where(Transaction.seller_id == current_user.id)
            elif current_user.role == UserRole.buyer:
                query = select(Transaction).where(Transaction.buyer_id == current_user.id)
            elif current_user.role == UserRole.tpqc or current_user.role == UserRole.admin:
                query = select(Transaction)
            else:
                query = select(Transaction)

            rows = session.exec(query).all()
            
            result = []
            for tx in rows:
                out = TransactionOut.model_validate(tx)
                listing = session.get(WasteListing, tx.listing_id)
                if listing:
                    out.material_type = listing.material_type
                    out.material_grade = listing.grade
                    out.purity_pct = listing.purity_pct
                    out.location_city = listing.location_city
                    out.location_country = listing.location_country
                    out.quantity_kg = listing.quantity_kg
                    out.created_at = listing.created_at
                    out.confidence_score = listing.confidence_score
                    from app.models.user import User
                    seller = session.get(User, tx.seller_id)
                    if seller:
                        out.seller_name = seller.name
                result.append(out)
            return result
    except Exception:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{transaction_id}", response_model=dict, status_code=status.HTTP_200_OK)
def get_transaction_detail(transaction_id: uuid.UUID, current_user: User = Depends(get_current_user)):
    """Get transaction details together with full audit trail."""
    try:
        with Session(engine) as session:
            tx = session.get(Transaction, transaction_id)
            if not tx:
                raise HTTPException(status_code=404, detail="Transaction not found")

            allowed = current_user.role == UserRole.admin
            allowed = allowed or (current_user.role == UserRole.manufacturer and tx.seller_id == current_user.id)
            allowed = allowed or (current_user.role == UserRole.buyer and tx.buyer_id == current_user.id)
            allowed = allowed or (current_user.role == UserRole.tpqc)
            if not allowed:
                raise HTTPException(status_code=403, detail="Forbidden")

            audits = session.exec(
                select(AuditTrail)
                .where(AuditTrail.transaction_id == transaction_id)
                .order_by(AuditTrail.created_at.asc())
            ).all()
            return {
                "transaction": TransactionOut.model_validate(tx).model_dump(),
                "audit": [
                    AuditOut(
                        id=a.id,
                        transaction_id=a.transaction_id,
                        listing_id=a.listing_id,
                        event_type=a.event_type.value,
                        actor_id=a.actor_id,
                        payload=a.payload,
                        hash=a.hash,
                        prev_hash=a.prev_hash,
                        created_at=a.created_at,
                    ).model_dump()
                    for a in audits
                ],
            }
    except HTTPException:
        raise
    except Exception:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{transaction_id}/lock", response_model=EscrowResult, status_code=status.HTTP_200_OK)
async def lock_transaction_escrow(transaction_id: uuid.UUID, current_user: User = Depends(get_current_user)):
    """Lock escrow for an agreed transaction as the assigned buyer."""
    try:
        with Session(engine) as session:
            tx = session.get(Transaction, transaction_id)
            if not tx:
                raise HTTPException(status_code=404, detail="Transaction not found")
            if current_user.id != tx.buyer_id:
                raise HTTPException(status_code=403, detail="Only assigned buyer can lock escrow")
            if tx.status != TransactionStatus.agreed:
                raise HTTPException(status_code=400, detail="Transaction must be AGREED before lock")
            result = await lock_escrow(transaction_id, session)

            tpqc_users = session.exec(select(User).where(User.role == UserRole.tpqc)).all()
            for tpqc_user in tpqc_users:
                session.add(
                    Notification(
                        user_id=tpqc_user.id,
                        transaction_id=tx.id,
                        message=f"Inspection pending for transaction {tx.id}",
                        notification_type="INSPECTION_PENDING",
                    )
                )
            session.add(
                Notification(
                    user_id=tx.seller_id,
                    transaction_id=tx.id,
                    message=f"Escrow locked for transaction {tx.id}. TPQC inspection will be scheduled.",
                    notification_type="ESCROW_LOCKED",
                )
            )
            session.add(
                Notification(
                    user_id=tx.buyer_id,
                    transaction_id=tx.id,
                    message=f"Escrow locked for transaction {tx.id}. Waiting for TPQC inspection.",
                    notification_type="ESCROW_LOCKED",
                )
            )
            session.commit()

            return result
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{transaction_id}/audit", response_model=list[AuditOut], status_code=status.HTTP_200_OK)
async def transaction_audit(transaction_id: uuid.UUID, current_user: User = Depends(get_current_user)):
    """Return the full audit chain for a transaction."""
    try:
        with Session(engine) as session:
            tx = session.get(Transaction, transaction_id)
            if not tx:
                raise HTTPException(status_code=404, detail="Transaction not found")
            chain = await get_audit_chain(transaction_id, session)
            return [
                AuditOut(
                    id=a.id,
                    transaction_id=a.transaction_id,
                    listing_id=a.listing_id,
                    event_type=a.event_type.value,
                    actor_id=a.actor_id,
                    payload=a.payload,
                    hash=a.hash,
                    prev_hash=a.prev_hash,
                    created_at=a.created_at,
                )
                for a in chain
            ]
    except HTTPException:
        raise
    except Exception:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{transaction_id}/dpp", status_code=status.HTTP_200_OK)
def download_dpp(transaction_id: uuid.UUID, current_user: User = Depends(get_current_user)):
    """Download generated DPP PDF for a transaction."""
    try:
        with Session(engine) as session:
            tx = session.get(Transaction, transaction_id)
            if not tx:
                raise HTTPException(status_code=404, detail="Transaction not found")
            if not tx.dpp_path:
                raise HTTPException(status_code=404, detail="DPP not available")
            if not os.path.exists(tx.dpp_path):
                raise HTTPException(status_code=404, detail="DPP file missing on disk")
            return FileResponse(path=tx.dpp_path, media_type="application/pdf", filename=f"{transaction_id}.pdf")
    except HTTPException:
        raise
    except Exception:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal server error")


# ==================== NEW HUMAN-IN-THE-LOOP ENDPOINTS ====================

class BuyerConfirmsInterestRequest(BaseModel):
    """Request to confirm buyer interest in a match."""
    pass


class ProposePriceResponse(BaseModel):
    """Response with proposed price details."""
    transaction: dict
    market_reference: dict
    proposed_price: float
    reasoning: str


class CounterOfferRequest(BaseModel):
    """Request to submit a counter-offer."""
    counter_price: float


class AcceptPriceRequest(BaseModel):
    """Request to accept the current price proposal."""
    pass


class PricingResponse(BaseModel):
    """Response with pricing details for a transaction."""
    market_reference: dict
    seller_floor: float
    buyer_ceiling: float
    initial_proposed_price: Optional[float]
    seller_counter_offer: Optional[float]
    buyer_counter_offer: Optional[float]
    current_status: str


class UpdateProfileRequest(BaseModel):
    max_price_per_kg: float


@router.post("/buyer-profile", response_model=dict, status_code=status.HTTP_200_OK)
def update_buyer_profile(payload: UpdateProfileRequest, current_user: User = Depends(get_current_user)):
    """Update the buyer's global negotiation profile (ceiling price)."""
    if current_user.role != UserRole.buyer:
        raise HTTPException(status_code=403, detail="Only buyers can update profiles")
    
    with Session(engine) as session:
        profile = session.exec(select(BuyerProfile).where(BuyerProfile.buyer_id == current_user.id)).first()
        if not profile:
            profile = BuyerProfile(
                buyer_id=current_user.id,
                material_needs="All",
                accepted_grades="A1,A2,B1",
                accepted_countries="Taiwan",
                max_price_per_kg=payload.max_price_per_kg,
                min_quantity_kg=0,
                max_quantity_kg=999999
            )
        else:
            profile.max_price_per_kg = payload.max_price_per_kg
        
        profile.updated_at = datetime.utcnow()
        session.add(profile)
        session.commit()
        return {"status": "success", "max_price_per_kg": profile.max_price_per_kg}


@router.post("/listing/{listing_id}/express-interest", response_model=TransactionOut, status_code=status.HTTP_200_OK)
def express_interest_in_listing(listing_id: uuid.UUID, current_user: User = Depends(get_current_user)):
    """Allow a buyer to directly express interest in a listing, creating a transaction if needed."""
    if current_user.role != UserRole.buyer:
        raise HTTPException(status_code=403, detail="Only buyers can express interest")
    
    try:
        with Session(engine) as session:
            listing = session.get(WasteListing, listing_id)
            if not listing:
                raise HTTPException(status_code=404, detail="Listing not found")
            
            # Check if transaction already exists
            tx = session.exec(
                select(Transaction)
                .where(Transaction.listing_id == listing_id)
                .where(Transaction.buyer_id == current_user.id)
            ).first()
            
            if not tx:
                tx = Transaction(
                    listing_id=listing_id,
                    seller_id=listing.seller_id,
                    buyer_id=current_user.id,
                    status=TransactionStatus.buyer_interested
                )
            else:
                if tx.status == TransactionStatus.matched:
                    tx.status = TransactionStatus.buyer_interested
                else:
                    # Already moved past interest
                    return TransactionOut.model_validate(tx)
            
            tx.buyer_confirmed_interest_at = datetime.utcnow()
            tx.updated_at = datetime.utcnow()
            session.add(tx)
            session.commit()
            session.refresh(tx)
            
            # Audit & Notification
            payload_data = {"transaction_id": str(tx.id), "buyer_id": str(tx.buyer_id), "source": "marketplace_direct"}
            prev = session.exec(select(AuditTrail).where(AuditTrail.transaction_id == tx.id).order_by(AuditTrail.created_at.desc())).first()
            prev_hash = prev.hash if prev else "GENESIS"
            session.add(AuditTrail(transaction_id=tx.id, listing_id=tx.listing_id, event_type=AuditEventType.negotiation_start, actor_id=current_user.id, payload=json.dumps(payload_data), hash=generate_event_hash(AuditEventType.negotiation_start.value, payload_data, prev_hash), prev_hash=prev_hash))
            
            notification = Notification(user_id=tx.seller_id, transaction_id=tx.id, message="Buyer expressed direct interest in your listing", notification_type="BUYER_CONFIRMED")
            session.add(notification)
            session.commit()
            
            return TransactionOut.model_validate(tx)
    except HTTPException:
        raise
    except Exception:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{transaction_id}/buyer-confirms-interest", response_model=TransactionOut, status_code=status.HTTP_200_OK)
def buyer_confirms_interest(
    transaction_id: uuid.UUID,
    payload: BuyerConfirmsInterestRequest,
    current_user: User = Depends(get_current_user)
):
    """Buyer confirms interest in a matched listing. Status MATCHED -> BUYER_INTERESTED."""
    try:
        with Session(engine) as session:
            tx = session.get(Transaction, transaction_id)
            if not tx:
                raise HTTPException(status_code=404, detail="Transaction not found")
            if current_user.id != tx.buyer_id:
                raise HTTPException(status_code=403, detail="Only assigned buyer can confirm interest")
            if tx.status != TransactionStatus.matched:
                raise HTTPException(status_code=400, detail=f"Transaction must be MATCHED, not {tx.status}")
            
            tx.status = TransactionStatus.buyer_interested
            tx.buyer_confirmed_interest_at = datetime.utcnow()
            tx.updated_at = datetime.utcnow()
            session.add(tx)
            session.commit()
            session.refresh(tx)
            
            # Audit event
            payload_data = {"transaction_id": str(tx.id), "buyer_id": str(tx.buyer_id)}
            prev = session.exec(select(AuditTrail).where(AuditTrail.transaction_id == tx.id).order_by(AuditTrail.created_at.desc())).first()
            prev_hash = prev.hash if prev else "GENESIS"
            session.add(AuditTrail(transaction_id=tx.id, listing_id=tx.listing_id, event_type=AuditEventType.negotiation_start, actor_id=current_user.id, payload=json.dumps(payload_data), hash=generate_event_hash(AuditEventType.negotiation_start.value, payload_data, prev_hash), prev_hash=prev_hash))
            
            # Notification
            notification = Notification(user_id=tx.seller_id, transaction_id=tx.id, message="Buyer confirmed interest", notification_type="BUYER_CONFIRMED")
            session.add(notification)
            session.commit()
            
            return TransactionOut.model_validate(tx)
    except HTTPException:
        raise
    except Exception:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{transaction_id}/propose-price", response_model=ProposePriceResponse, status_code=status.HTTP_200_OK)
def propose_price(transaction_id: uuid.UUID, current_user: User = Depends(get_current_user)):
    """Propose ZOPA price. Status BUYER_INTERESTED -> PRICE_PROPOSED."""
    try:
        settings = get_settings()
        with Session(engine) as session:
            tx = session.get(Transaction, transaction_id)
            if not tx:
                raise HTTPException(status_code=404, detail="Transaction not found")
            if tx.status not in {TransactionStatus.buyer_interested, TransactionStatus.price_proposed}:
                raise HTTPException(status_code=400, detail=f"Transaction must be BUYER_INTERESTED or PRICE_PROPOSED, not {tx.status}")
            
            listing = session.get(WasteListing, tx.listing_id)
            if not listing:
                raise HTTPException(status_code=404, detail="Listing not found")
            
            buyer_profile = session.exec(select(BuyerProfile).where(BuyerProfile.buyer_id == tx.buyer_id)).first()
            if not buyer_profile:
                raise HTTPException(status_code=400, detail="Buyer profile not found")
            
            seller_floor = listing.ask_price_per_kg
            buyer_ceiling = buyer_profile.max_price_per_kg
            
            market_data = get_market_price_range(listing.material_category, listing.grade or "A1")
            market_low = market_data["low_price_per_kg"] if market_data["found"] else 0
            market_high = market_data["high_price_per_kg"] if market_data["found"] else 0
            
            zopa_result = calculate_zopa(seller_floor, buyer_ceiling, market_low, market_high)
            
            if not zopa_result["has_zopa"]:
                tx.status = TransactionStatus.failed
                session.add(tx)
                for user_id in [tx.seller_id, tx.buyer_id]:
                    notification = Notification(user_id=user_id, transaction_id=tx.id, message="No price overlap. Deal failed.", notification_type="NO_ZOPA")
                    session.add(notification)
                session.commit()
                raise HTTPException(status_code=400, detail=zopa_result["reasoning"])
            
            proposed_price = zopa_result["proposed_price"]
            tx.status = TransactionStatus.price_proposed
            tx.initial_proposed_price = proposed_price
            tx.counter_offer_expires_at = datetime.utcnow() + timedelta(hours=24)
            tx.updated_at = datetime.utcnow()
            session.add(tx)
            session.commit()
            session.refresh(tx)
            
            payload_data = {"transaction_id": str(tx.id), "proposed_price": proposed_price}
            prev = session.exec(select(AuditTrail).where(AuditTrail.transaction_id == tx.id).order_by(AuditTrail.created_at.desc())).first()
            prev_hash = prev.hash if prev else "GENESIS"
            session.add(AuditTrail(transaction_id=tx.id, listing_id=tx.listing_id, event_type=AuditEventType.negotiation_round, actor_id=current_user.id, payload=json.dumps(payload_data), hash=generate_event_hash(AuditEventType.negotiation_round.value, payload_data, prev_hash), prev_hash=prev_hash))
            
            for user_id in [tx.seller_id, tx.buyer_id]:
                notification = Notification(user_id=user_id, transaction_id=tx.id, message=f"Price proposal: ${proposed_price:.2f}/kg", notification_type="PRICE_PROPOSED")
                session.add(notification)
            session.commit()
            
            return ProposePriceResponse(transaction=TransactionOut.model_validate(tx).model_dump(), market_reference=market_data, proposed_price=proposed_price, reasoning=zopa_result["reasoning"])
    except HTTPException:
        raise
    except Exception:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{transaction_id}/counter-offer", response_model=TransactionOut, status_code=status.HTTP_200_OK)
def counter_offer(transaction_id: uuid.UUID, payload: CounterOfferRequest, current_user: User = Depends(get_current_user)):
    """Submit counter-offer. One per party."""
    try:
        with Session(engine) as session:
            tx = session.get(Transaction, transaction_id)
            if not tx:
                raise HTTPException(status_code=404, detail="Transaction not found")
            if tx.status not in {TransactionStatus.price_proposed, TransactionStatus.price_countered}:
                raise HTTPException(status_code=400, detail=f"Invalid status: {tx.status}")
            
            if current_user.id == tx.seller_id:
                if tx.counter_offer_from_seller is not None:
                    raise HTTPException(status_code=400, detail="Seller already countered")
                tx.counter_offer_from_seller = payload.counter_price
                party_role = "seller"
            elif current_user.id == tx.buyer_id:
                if tx.counter_offer_from_buyer is not None:
                    raise HTTPException(status_code=400, detail="Buyer already countered")
                tx.counter_offer_from_buyer = payload.counter_price
                party_role = "buyer"
            else:
                raise HTTPException(status_code=403, detail="Invalid party")
            
            if tx.counter_offer_from_seller is not None and tx.counter_offer_from_buyer is not None:
                zopa_result = check_counter_offer_zopa(tx.initial_proposed_price, tx.counter_offer_from_seller, tx.initial_proposed_price, tx.counter_offer_from_buyer)
                tx.status = TransactionStatus.agreed if zopa_result["has_zopa"] else TransactionStatus.failed
                if zopa_result["has_zopa"]:
                    tx.agreed_price_per_kg = zopa_result["effective_low"]
            else:
                tx.status = TransactionStatus.price_countered
            
            tx.updated_at = datetime.utcnow()
            session.add(tx)
            session.commit()
            session.refresh(tx)
            
            payload_data = {"transaction_id": str(tx.id), "party": party_role, "counter_price": payload.counter_price}
            prev = session.exec(select(AuditTrail).where(AuditTrail.transaction_id == tx.id).order_by(AuditTrail.created_at.desc())).first()
            prev_hash = prev.hash if prev else "GENESIS"
            session.add(AuditTrail(transaction_id=tx.id, listing_id=tx.listing_id, event_type=AuditEventType.negotiation_round, actor_id=current_user.id, payload=json.dumps(payload_data), hash=generate_event_hash(AuditEventType.negotiation_round.value, payload_data, prev_hash), prev_hash=prev_hash))
            
            other_party_id = tx.buyer_id if current_user.id == tx.seller_id else tx.seller_id
            notification = Notification(user_id=other_party_id, transaction_id=tx.id, message=f"{party_role.capitalize()} counter-offered ${payload.counter_price:.2f}/kg", notification_type="PRICE_COUNTERED")
            session.add(notification)
            session.commit()
            
            return TransactionOut.model_validate(tx)
    except HTTPException:
        raise
    except Exception:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{transaction_id}/accept-price", response_model=TransactionOut, status_code=status.HTTP_200_OK)
def accept_price(transaction_id: uuid.UUID, payload: AcceptPriceRequest, current_user: User = Depends(get_current_user)):
    """Accept price. Both must accept for AGREED status."""
    try:
        settings = get_settings()
        with Session(engine) as session:
            tx = session.get(Transaction, transaction_id)
            if not tx:
                raise HTTPException(status_code=404, detail="Transaction not found")
            if tx.status not in {TransactionStatus.price_proposed, TransactionStatus.price_countered}:
                raise HTTPException(status_code=400, detail=f"Invalid status: {tx.status}")
            
            listing = session.get(WasteListing, tx.listing_id)
            if not listing:
                raise HTTPException(status_code=404, detail="Listing not found")
            
            accepted_price = (tx.counter_offer_from_seller if tx.counter_offer_from_seller else 
                             (tx.counter_offer_from_buyer if tx.counter_offer_from_buyer else tx.initial_proposed_price))
            
            if current_user.id == tx.seller_id:
                tx.seller_accepted_price_at = datetime.utcnow()
            elif current_user.id == tx.buyer_id:
                tx.buyer_accepted_price_at = datetime.utcnow()
            else:
                raise HTTPException(status_code=403, detail="Invalid party")
            
            if tx.seller_accepted_price_at and tx.buyer_accepted_price_at:
                tx.status = TransactionStatus.agreed
                tx.agreed_price_per_kg = accepted_price
                tx.total_value = accepted_price * listing.quantity_kg
                tx.platform_fee = (settings.PLATFORM_FEE_PCT / 100.0) * tx.total_value
                tx.seller_payout = tx.total_value - tx.platform_fee
                event_type = AuditEventType.deal_agreed
            else:
                event_type = AuditEventType.negotiation_round
            
            tx.updated_at = datetime.utcnow()
            session.add(tx)
            session.commit()
            session.refresh(tx)
            
            payload_data = {"transaction_id": str(tx.id), "accepted_price": accepted_price}
            prev = session.exec(select(AuditTrail).where(AuditTrail.transaction_id == tx.id).order_by(AuditTrail.created_at.desc())).first()
            prev_hash = prev.hash if prev else "GENESIS"
            session.add(AuditTrail(transaction_id=tx.id, listing_id=tx.listing_id, event_type=event_type, actor_id=current_user.id, payload=json.dumps(payload_data), hash=generate_event_hash(event_type.value, payload_data, prev_hash), prev_hash=prev_hash))
            
            other_party_id = tx.buyer_id if current_user.id == tx.seller_id else tx.seller_id
            notification = Notification(user_id=other_party_id, transaction_id=tx.id, message=f"Price accepted at ${accepted_price:.2f}/kg" if tx.status != TransactionStatus.agreed else "Deal agreed!", notification_type="DEAL_AGREED" if tx.status == TransactionStatus.agreed else "PRICE_ACCEPTED")
            session.add(notification)
            session.commit()
            
            return TransactionOut.model_validate(tx)
    except HTTPException:
        raise
    except Exception:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{transaction_id}/pricing", response_model=PricingResponse, status_code=status.HTTP_200_OK)
def get_pricing(transaction_id: uuid.UUID, current_user: User = Depends(get_current_user)):
    """Get pricing details."""
    try:
        with Session(engine) as session:
            tx = session.get(Transaction, transaction_id)
            if not tx:
                raise HTTPException(status_code=404, detail="Transaction not found")
            
            allowed = current_user.role == UserRole.admin or (current_user.role == UserRole.manufacturer and tx.seller_id == current_user.id) or (current_user.role == UserRole.buyer and tx.buyer_id == current_user.id)
            if not allowed:
                raise HTTPException(status_code=403, detail="Forbidden")
            
            listing = session.get(WasteListing, tx.listing_id)
            if not listing:
                raise HTTPException(status_code=404, detail="Listing not found")
            
            buyer_profile = session.exec(select(BuyerProfile).where(BuyerProfile.buyer_id == tx.buyer_id)).first()
            if not buyer_profile:
                raise HTTPException(status_code=404, detail="Buyer profile not found")
            
            market_data = get_market_price_range(listing.material_category, listing.grade or "A1")
            
            return PricingResponse(market_reference=market_data, seller_floor=listing.ask_price_per_kg, buyer_ceiling=buyer_profile.max_price_per_kg, initial_proposed_price=tx.initial_proposed_price, seller_counter_offer=tx.counter_offer_from_seller, buyer_counter_offer=tx.counter_offer_from_buyer, current_status=tx.status.value)
    except HTTPException:
        raise
    except Exception:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal server error")
