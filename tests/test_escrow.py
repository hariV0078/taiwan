import uuid
import os

import pytest
from sqlmodel import Session, SQLModel, create_engine

os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")
os.environ.setdefault("SECRET_KEY", "test-secret-key-min-32-characters")

from app.models.audit import AuditTrail
from app.models.listing import WasteListing
from app.models.transaction import Transaction, TransactionStatus
from app.models.user import User, UserRole
from app.services.escrow import get_audit_chain, lock_escrow, release_escrow, verify_escrow


@pytest.fixture
def session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        seller = User(name="Seller", email="s@test.com", password_hash="x", role=UserRole.manufacturer, company="SCo", country="IN")
        buyer = User(name="Buyer", email="b@test.com", password_hash="x", role=UserRole.buyer, company="BCo", country="IN")
        session.add(seller)
        session.add(buyer)
        session.commit()
        session.refresh(seller)
        session.refresh(buyer)

        listing = WasteListing(
            seller_id=seller.id,
            material_type="Steel",
            material_category="Metal/Steel",
            quantity_kg=1000,
            purity_pct=85,
            location_city="Pune",
            location_country="IN",
            ask_price_per_kg=0.4,
        )
        session.add(listing)
        session.commit()
        session.refresh(listing)

        tx = Transaction(
            listing_id=listing.id,
            seller_id=seller.id,
            buyer_id=buyer.id,
            status=TransactionStatus.agreed,
        )
        session.add(tx)
        session.commit()
        session.refresh(tx)
        yield session, tx.id, buyer.id


@pytest.mark.asyncio
async def test_valid_transitions_succeed(session):
    s, tx_id, inspector_id = session
    locked = await lock_escrow(tx_id, s)
    assert locked.new_status == TransactionStatus.locked

    verified = await verify_escrow(tx_id, inspector_id, "ok", s)
    assert verified.new_status == TransactionStatus.verified

    released = await release_escrow(tx_id, s)
    assert released.new_status == TransactionStatus.released


@pytest.mark.asyncio
async def test_invalid_transition_raises(session):
    s, tx_id, _inspector_id = session
    await lock_escrow(tx_id, s)
    with pytest.raises(ValueError):
        await lock_escrow(tx_id, s)


@pytest.mark.asyncio
async def test_hash_chain_append_only(session):
    s, tx_id, inspector_id = session
    await lock_escrow(tx_id, s)
    await verify_escrow(tx_id, inspector_id, "ok", s)
    await release_escrow(tx_id, s)

    chain = await get_audit_chain(tx_id, s)
    assert len(chain) >= 3
    for idx in range(1, len(chain)):
        assert chain[idx].prev_hash == chain[idx - 1].hash
