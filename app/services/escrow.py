import json
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel
from sqlmodel import Session, select

from app.models.audit import AuditEventType, AuditTrail
from app.models.transaction import Transaction, TransactionStatus
from app.utils.hashing import generate_event_hash


class EscrowResult(BaseModel):
    transaction_id: uuid.UUID
    new_status: TransactionStatus
    hash: str
    timestamp: datetime
    message: str


VALID_TRANSITIONS = {
    TransactionStatus.matched: [TransactionStatus.buyer_interested, TransactionStatus.failed],
    TransactionStatus.buyer_interested: [TransactionStatus.price_proposed, TransactionStatus.failed],
    TransactionStatus.price_proposed: [TransactionStatus.price_countered, TransactionStatus.agreed, TransactionStatus.failed],
    TransactionStatus.price_countered: [TransactionStatus.price_countered, TransactionStatus.agreed, TransactionStatus.failed],
    TransactionStatus.agreed: [TransactionStatus.locked],
    TransactionStatus.locked: [TransactionStatus.inspecting, TransactionStatus.disputed],
    TransactionStatus.inspecting: [TransactionStatus.verified, TransactionStatus.disputed],
    TransactionStatus.verified: [TransactionStatus.released],
    TransactionStatus.released: [],
    TransactionStatus.disputed: [TransactionStatus.verified, TransactionStatus.failed],
    TransactionStatus.failed: [],
}


def _get_transaction(transaction_id: uuid.UUID, session: Session) -> Transaction:
    tx = session.get(Transaction, transaction_id)
    if not tx:
        raise ValueError("Transaction not found")
    return tx


def _latest_hash(transaction_id: uuid.UUID, session: Session) -> str:
    prev = session.exec(
        select(AuditTrail)
        .where(AuditTrail.transaction_id == transaction_id)
        .order_by(AuditTrail.created_at.desc())
    ).first()
    return prev.hash if prev else "GENESIS"


def _event_type_for_status(status: TransactionStatus) -> AuditEventType:
    mapping = {
        TransactionStatus.locked: AuditEventType.escrow_locked,
        TransactionStatus.verified: AuditEventType.tpqc_verified,
        TransactionStatus.disputed: AuditEventType.tpqc_rejected,
        TransactionStatus.released: AuditEventType.escrow_released,
    }
    return mapping[status]


def _assert_transition(current: TransactionStatus, target: TransactionStatus) -> None:
    allowed = VALID_TRANSITIONS.get(current, [])
    if target not in allowed:
        raise ValueError(f"Invalid transition from {current} to {target}")


def _apply_transition(
    tx: Transaction,
    target_status: TransactionStatus,
    payload: dict,
    session: Session,
    message: str,
) -> EscrowResult:
    _assert_transition(tx.status, target_status)

    now = datetime.utcnow()
    tx.status = target_status
    if target_status == TransactionStatus.locked:
        tx.locked_at = now
    elif target_status == TransactionStatus.verified:
        tx.verified_at = now
    elif target_status == TransactionStatus.released:
        tx.released_at = now

    prev_hash = _latest_hash(tx.id, session)
    event_type = _event_type_for_status(target_status)
    event_hash = generate_event_hash(event_type.value, payload, prev_hash)

    if target_status == TransactionStatus.locked:
        tx.escrow_hash = event_hash
    if target_status in {TransactionStatus.verified, TransactionStatus.disputed}:
        tx.qar_hash = event_hash

    audit = AuditTrail(
        transaction_id=tx.id,
        listing_id=tx.listing_id,
        event_type=event_type,
        actor_id=payload.get("inspector_id"),
        payload=json.dumps(payload),
        hash=event_hash,
        prev_hash=prev_hash,
    )

    session.add(tx)
    session.add(audit)
    session.commit()
    session.refresh(tx)

    return EscrowResult(
        transaction_id=tx.id,
        new_status=tx.status,
        hash=event_hash,
        timestamp=now,
        message=message,
    )


async def lock_escrow(transaction_id: uuid.UUID, session: Session) -> EscrowResult:
    tx = _get_transaction(transaction_id, session)
    payload = {"transaction_id": str(transaction_id), "action": "lock_escrow"}
    return _apply_transition(tx, TransactionStatus.locked, payload, session, "Escrow locked")


async def verify_escrow(
    transaction_id: uuid.UUID,
    inspector_id: uuid.UUID,
    qar_notes: str,
    session: Session,
) -> EscrowResult:
    tx = _get_transaction(transaction_id, session)
    tx.qar_notes = qar_notes
    payload = {
        "transaction_id": str(transaction_id),
        "inspector_id": str(inspector_id),
        "qar_notes": qar_notes,
        "action": "verify_escrow",
    }
    return _apply_transition(tx, TransactionStatus.verified, payload, session, "Escrow verified")


async def reject_escrow(
    transaction_id: uuid.UUID,
    inspector_id: uuid.UUID,
    reason: str,
    session: Session,
) -> EscrowResult:
    tx = _get_transaction(transaction_id, session)
    tx.qar_notes = reason
    payload = {
        "transaction_id": str(transaction_id),
        "inspector_id": str(inspector_id),
        "reason": reason,
        "action": "reject_escrow",
    }
    return _apply_transition(tx, TransactionStatus.disputed, payload, session, "Escrow rejected/disputed")


async def release_escrow(transaction_id: uuid.UUID, session: Session) -> EscrowResult:
    tx = _get_transaction(transaction_id, session)
    payload = {"transaction_id": str(transaction_id), "action": "release_escrow"}
    return _apply_transition(tx, TransactionStatus.released, payload, session, "Escrow released")


async def get_audit_chain(transaction_id: uuid.UUID, session: Session) -> list[AuditTrail]:
    return list(
        session.exec(
            select(AuditTrail)
            .where(AuditTrail.transaction_id == transaction_id)
            .order_by(AuditTrail.created_at.asc())
        ).all()
    )
