import os
import sys

# Ensure correct working directory context
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import engine
from sqlmodel import Session, select
from app.models.user import User
from app.models.listing import WasteListing, MaterialGrade, ListingStatus
from app.models.transaction import Transaction, TransactionStatus, BuyerProfile
from datetime import datetime, timedelta

def seed_data():
    with Session(engine) as session:
        # Get users
        alice = session.exec(select(User).where(User.email == "alice@greentech.com")).first()
        bob = session.exec(select(User).where(User.email == "bob@ecorecycle.com")).first()
        charlie = session.exec(select(User).where(User.email == "charlie@tpqc.com")).first()
        
        if not alice or not bob or not charlie:
            print("Users not found. Please run seed_users.py first.")
            return

        # Create a Listing by Alice
        listing = WasteListing(
            seller_id=alice.id,
            material_type="High-Density Polyethylene (HDPE)",
            material_category="Plastics",
            grade=MaterialGrade.A1,
            quantity_kg=5000.0,
            purity_pct=95.5,
            location_city="Taipei",
            location_country="Taiwan",
            ask_price_per_kg=0.85,
            status=ListingStatus.active,
            description="Clean post-industrial HDPE pellets. Minimal contamination.",
            expires_at=datetime.utcnow() + timedelta(days=30)
        )
        session.add(listing)
        session.commit()
        session.refresh(listing)
        print("Created Listing by Alice.")

        # Create Buyer Profile for Bob
        profile = BuyerProfile(
            buyer_id=bob.id,
            material_needs="HDPE, PET",
            accepted_grades="A1,A2",
            accepted_countries="Taiwan,Global",
            max_price_per_kg=1.00,
            min_quantity_kg=1000.0,
            max_quantity_kg=10000.0
        )
        # Avoid duplicate profile
        existing_profile = session.exec(select(BuyerProfile).where(BuyerProfile.buyer_id == bob.id)).first()
        if not existing_profile:
            session.add(profile)
            session.commit()
            print("Created Buyer Profile for Bob.")

        # Create a Transaction between Alice and Bob
        tx = Transaction(
            listing_id=listing.id,
            seller_id=alice.id,
            buyer_id=bob.id,
            status=TransactionStatus.price_proposed,
            initial_proposed_price=0.82,
            matched_at=datetime.utcnow() - timedelta(minutes=30),
            buyer_confirmed_interest_at=datetime.utcnow() - timedelta(minutes=20)
        )
        session.add(tx)
        session.commit()
        print("Created active Transaction between Alice and Bob.")
        
        print("Done seeding data!")

if __name__ == "__main__":
    seed_data()
