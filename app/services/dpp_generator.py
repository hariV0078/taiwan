import json
import os
import tempfile
import uuid
from datetime import datetime

import qrcode
from fpdf import FPDF
from pydantic import BaseModel
from sqlmodel import Session, select

from app.config import get_settings
from app.models.audit import AuditEventType, AuditTrail
from app.models.listing import WasteListing
from app.models.transaction import Transaction
from app.models.user import User
from app.utils.hashing import generate_event_hash

settings = get_settings()

CO2_FACTORS = {
    "plastic": 1.9,
    "hdpe": 1.9,
    "ldpe": 1.8,
    "pp": 1.7,
    "pet": 2.1,
    "steel": 1.46,
    "iron": 1.2,
    "aluminium": 8.24,
    "aluminum": 8.24,
    "copper": 3.5,
    "paper": 0.9,
    "cardboard": 0.85,
    "glass": 0.5,
    "rubber": 1.2,
    "default": 1.0,
}


class DPPResult(BaseModel):
    transaction_id: uuid.UUID
    pdf_path: str
    co2_saved_kg: float
    value_unlocked_usd: float
    dpp_id: str


def _factor_for_category(category: str) -> float:
    lowered = (category or "").lower()
    for key, value in CO2_FACTORS.items():
        if key != "default" and key in lowered:
            return value
    return CO2_FACTORS["default"]


def generate_dpp(transaction_id: uuid.UUID, session: Session) -> DPPResult:
    tx = session.get(Transaction, transaction_id)
    if not tx:
        raise ValueError("Transaction not found")

    listing = session.get(WasteListing, tx.listing_id)
    if not listing:
        raise ValueError("Listing not found")

    seller = session.get(User, tx.seller_id)
    buyer = session.get(User, tx.buyer_id)
    if not seller or not buyer:
        raise ValueError("Seller or buyer not found")

    factor = _factor_for_category(listing.material_category)
    co2_saved_kg = listing.quantity_kg * factor
    trees_equivalent = co2_saved_kg / 21.77
    total_value = tx.total_value or ((tx.agreed_price_per_kg or 0) * listing.quantity_kg)

    dpp_id = str(uuid.uuid4())
    verify_payload = {
        "dpp_id": dpp_id,
        "transaction_id": str(transaction_id),
        "verify_url": f"https://circularx.io/verify/{dpp_id}",
    }

    os.makedirs(settings.DPP_STORAGE_PATH, exist_ok=True)
    pdf_path = os.path.join(settings.DPP_STORAGE_PATH, f"{transaction_id}.pdf")

    qr_img = qrcode.make(json.dumps(verify_payload))
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        qr_path = tmp.name
    qr_img.save(qr_path)

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(120, 10, "CircularX Digital Product Passport", ln=0)
    pdf.image(qr_path, x=165, y=8, w=35, h=35)

    pdf.set_font("Helvetica", size=10)
    pdf.ln(12)
    pdf.cell(0, 8, f"DPP ID: {dpp_id}", ln=1)
    pdf.cell(0, 8, f"Generated At: {datetime.utcnow().isoformat()}Z", ln=1)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Material", ln=1)
    pdf.set_font("Helvetica", size=10)
    pdf.multi_cell(
        0,
        7,
        (
            f"Type: {listing.material_type}\n"
            f"Category: {listing.material_category}\n"
            f"Grade: {listing.grade}\n"
            f"Quantity (kg): {listing.quantity_kg}\n"
            f"Purity (%): {listing.purity_pct}\n"
            f"Origin: {listing.location_city}, {listing.location_country}"
        ),
    )

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Transaction", ln=1)
    pdf.set_font("Helvetica", size=10)
    pdf.multi_cell(
        0,
        7,
        (
            f"Seller Company: {seller.company}\n"
            f"Buyer Company: {buyer.company}\n"
            f"Agreed Price per kg: {tx.agreed_price_per_kg}\n"
            f"Total Value: {total_value}\n"
            f"Platform Fee: {tx.platform_fee}\n"
            f"Seller Payout: {tx.seller_payout}"
        ),
    )

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Trust and Verification", ln=1)
    pdf.set_font("Helvetica", size=10)
    pdf.multi_cell(
        0,
        7,
        (
            f"Escrow Hash: {tx.escrow_hash}\n"
            f"QAR Hash: {tx.qar_hash}\n"
            f"TPQC Notes: {tx.qar_notes}\n"
            f"Verified Timestamp: {tx.verified_at}"
        ),
    )

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Environmental Impact", ln=1)
    pdf.set_font("Helvetica", size=10)
    pdf.multi_cell(
        0,
        7,
        (
            f"CO2 Saved (kg): {co2_saved_kg:.2f}\n"
            f"CO2 Saved (tonnes): {co2_saved_kg / 1000:.4f}\n"
            f"Equivalent Trees Planted: {trees_equivalent:.2f}\n"
            f"Waste Diverted from Landfill (kg): {listing.quantity_kg:.2f}"
        ),
    )

    audits = list(
        session.exec(
            select(AuditTrail)
            .where(AuditTrail.transaction_id == tx.id)
            .order_by(AuditTrail.created_at.desc())
            .limit(5)
        ).all()
    )
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Audit Trail (Last 5)", ln=1)
    pdf.set_font("Helvetica", size=9)
    for audit in audits:
        pdf.multi_cell(0, 6, f"{audit.created_at} | {audit.event_type.value} | {audit.hash}")

    pdf.output(pdf_path)
    os.remove(qr_path)

    tx.dpp_path = pdf_path
    tx.co2_saved_kg = co2_saved_kg

    prev = session.exec(
        select(AuditTrail)
        .where(AuditTrail.transaction_id == tx.id)
        .order_by(AuditTrail.created_at.desc())
    ).first()
    prev_hash = prev.hash if prev else "GENESIS"

    payload = {
        "transaction_id": str(tx.id),
        "dpp_id": dpp_id,
        "pdf_path": pdf_path,
        "co2_saved_kg": co2_saved_kg,
    }
    event_hash = generate_event_hash(AuditEventType.dpp_generated.value, payload, prev_hash)

    session.add(tx)
    session.add(
        AuditTrail(
            transaction_id=tx.id,
            listing_id=tx.listing_id,
            event_type=AuditEventType.dpp_generated,
            payload=json.dumps(payload),
            hash=event_hash,
            prev_hash=prev_hash,
        )
    )
    session.commit()

    return DPPResult(
        transaction_id=tx.id,
        pdf_path=pdf_path,
        co2_saved_kg=co2_saved_kg,
        value_unlocked_usd=float(total_value),
        dpp_id=dpp_id,
    )
