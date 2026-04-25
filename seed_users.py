import os
import sys

# Ensure correct working directory context
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import engine
from sqlmodel import Session, select
from app.models.user import User, UserRole
from app.routers.auth import get_password_hash

def seed_users():
    password_hash = get_password_hash("pass123")
    with Session(engine) as session:
        users_to_add = [
            User(
                name="Alice Seller",
                email="alice@greentech.com",
                password_hash=password_hash,
                role=UserRole.manufacturer,
                company="GreenTech Manufacturing",
                country="Taiwan"
            ),
            User(
                name="Bob Buyer",
                email="bob@ecorecycle.com",
                password_hash=password_hash,
                role=UserRole.buyer,
                company="EcoRecycle Corp",
                country="India"
            ),
            User(
                name="Charlie Inspector",
                email="charlie@tpqc.com",
                password_hash=password_hash,
                role=UserRole.tpqc,
                company="TPQC Global",
                country="Global"
            ),
            User(
                name="Admin User",
                email="admin@circularx.com",
                password_hash=password_hash,
                role=UserRole.admin,
                company="CircularX HQ",
                country="Taiwan"
            )
        ]

        added_count = 0
        for u in users_to_add:
            existing = session.exec(select(User).where(User.email == u.email)).first()
            if existing:
                existing.password_hash = u.password_hash
                existing.name = u.name
                existing.company = u.company
                existing.role = u.role
                added_count += 1
            else:
                session.add(u)
                added_count += 1
        
        session.commit()
        print(f"Seeded {added_count} users successfully into the database.")

if __name__ == "__main__":
    seed_users()
