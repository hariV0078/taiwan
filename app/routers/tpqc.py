import traceback
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlmodel import Session, select

from app.database import engine
from app.models.notification import Notification
from app.models.transaction import Transaction, TransactionStatus
from app.models.user import User, UserRole
from app.routers.auth import get_current_user
from app.services.dpp_generator import DPPResult, generate_dpp
from app.services.escrow import EscrowResult, reject_escrow, release_escrow, verify_escrow

router = APIRouter()


class ApproveRequest(BaseModel):
    qar_notes: str

    model_config = ConfigDict(json_schema_extra={"example": {"qar_notes": "Moisture within tolerance, grade confirmed."}})


class RejectRequest(BaseModel):
    reason: str

    model_config = ConfigDict(json_schema_extra={"example": {"reason": "Purity too low; heavy contamination."}})


class TPQCTransactionOut(BaseModel):
    id: uuid.UUID
    listing_id: uuid.UUID
    seller_id: uuid.UUID
    buyer_id: uuid.UUID
    status: TransactionStatus
    qar_notes: Optional[str]
    qar_hash: Optional[str]
    dpp_path: Optional[str]
    co2_saved_kg: Optional[float]
    verified_at: Optional[datetime]
    released_at: Optional[datetime]


@router.get("/pending", response_model=list[TPQCTransactionOut], status_code=status.HTTP_200_OK)
def pending_tpqc(current_user: User = Depends(get_current_user)):
    """List all LOCKED transactions pending TPQC inspection."""
    if current_user.role != UserRole.tpqc:
        raise HTTPException(status_code=403, detail="TPQC role required")
    try:
        with Session(engine) as session:
            rows = session.exec(
                select(Transaction).where(Transaction.status == TransactionStatus.locked)
            ).all()
            return [TPQCTransactionOut.model_validate(x) for x in rows]
    except Exception:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{transaction_id}/start-inspection", response_model=TPQCTransactionOut, status_code=status.HTTP_200_OK)
def start_inspection(
    transaction_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
):
    """Start TPQC inspection. Status LOCKED -> INSPECTING."""
    if current_user.role != UserRole.tpqc:
        raise HTTPException(status_code=403, detail="TPQC role required")

    try:
        with Session(engine) as session:
            tx = session.get(Transaction, transaction_id)
            if not tx:
                raise HTTPException(status_code=404, detail="Transaction not found")
            if tx.status != TransactionStatus.locked:
                raise HTTPException(status_code=400, detail="Transaction must be LOCKED")
            
            tx.status = TransactionStatus.inspecting
            session.add(tx)
            session.commit()
            session.refresh(tx)

            session.add(
                Notification(
                    user_id=tx.seller_id,
                    transaction_id=tx.id,
                    message=f"TPQC inspection started for transaction {tx.id}",
                    notification_type="INSPECTION_STARTED",
                )
            )
            session.add(
                Notification(
                    user_id=tx.buyer_id,
                    transaction_id=tx.id,
                    message=f"TPQC inspection started for transaction {tx.id}",
                    notification_type="INSPECTION_STARTED",
                )
            )
            session.commit()
            
            return TPQCTransactionOut.model_validate(tx)
    except HTTPException:
        raise
    except Exception:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{transaction_id}/approve", response_model=TPQCTransactionOut, status_code=status.HTTP_200_OK)
async def approve_tpqc(
    transaction_id: uuid.UUID,
    payload: ApproveRequest,
    current_user: User = Depends(get_current_user),
):
    """Approve TPQC inspection, release escrow, and generate DPP."""
    if current_user.role != UserRole.tpqc:
        raise HTTPException(status_code=403, detail="TPQC role required")

    try:
        with Session(engine) as session:
            tx = session.get(Transaction, transaction_id)
            if not tx:
                raise HTTPException(status_code=404, detail="Transaction not found")
            if tx.status != TransactionStatus.inspecting:
                raise HTTPException(status_code=400, detail="Transaction must be INSPECTING")

            await verify_escrow(transaction_id, current_user.id, payload.qar_notes, session)
            await release_escrow(transaction_id, session)
            dpp: DPPResult = generate_dpp(transaction_id, session)

            tx = session.get(Transaction, transaction_id)
            tx.dpp_path = dpp.pdf_path
            tx.co2_saved_kg = dpp.co2_saved_kg
            session.add(tx)
            session.add(
                Notification(
                    user_id=tx.seller_id,
                    transaction_id=tx.id,
                    message=f"Transaction {tx.id} verified. DPP generated.",
                    notification_type="VERIFIED",
                )
            )
            session.add(
                Notification(
                    user_id=tx.buyer_id,
                    transaction_id=tx.id,
                    message=f"Transaction {tx.id} verified. DPP generated.",
                    notification_type="VERIFIED",
                )
            )
            session.commit()
            session.refresh(tx)
            return TPQCTransactionOut.model_validate(tx)
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{transaction_id}/reject", response_model=EscrowResult, status_code=status.HTTP_200_OK)
async def reject_tpqc(
    transaction_id: uuid.UUID,
    payload: RejectRequest,
    current_user: User = Depends(get_current_user),
):
    """Reject TPQC inspection and place transaction into disputed state."""
    if current_user.role != UserRole.tpqc:
        raise HTTPException(status_code=403, detail="TPQC role required")

    try:
        with Session(engine) as session:
            tx = session.get(Transaction, transaction_id)
            if not tx:
                raise HTTPException(status_code=404, detail="Transaction not found")
            if tx.status not in {TransactionStatus.locked, TransactionStatus.inspecting}:
                raise HTTPException(status_code=400, detail="Transaction must be LOCKED or INSPECTING")
            result = await reject_escrow(transaction_id, current_user.id, payload.reason, session)
            session.add(
                Notification(
                    user_id=tx.seller_id,
                    transaction_id=tx.id,
                    message=f"Transaction {tx.id} was disputed: {payload.reason}",
                    notification_type="DISPUTED",
                )
            )
            session.add(
                Notification(
                    user_id=tx.buyer_id,
                    transaction_id=tx.id,
                    message=f"Transaction {tx.id} was disputed: {payload.reason}",
                    notification_type="DISPUTED",
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


@router.get("/{transaction_id}/qar", response_model=dict, status_code=status.HTTP_200_OK)
def get_qar(transaction_id: uuid.UUID, current_user: User = Depends(get_current_user)):
    """Get QAR notes and verification hashes for a transaction."""
    if current_user.role not in {UserRole.tpqc, UserRole.admin}:
        raise HTTPException(status_code=403, detail="Forbidden")
    try:
        with Session(engine) as session:
            tx = session.get(Transaction, transaction_id)
            if not tx:
                raise HTTPException(status_code=404, detail="Transaction not found")
            return {
                "transaction_id": str(tx.id),
                "status": tx.status.value,
                "qar_notes": tx.qar_notes,
                "qar_hash": tx.qar_hash,
                "verified_at": tx.verified_at,
            }
    except HTTPException:
        raise
    except Exception:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal server error")
