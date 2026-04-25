"""
User seeding utility for loading test users from fixtures.
This allows reproducible test data to be tracked in git.
"""

import json
from pathlib import Path
from sqlmodel import Session, select
from app.database import engine
from app.models.user import User, UserRole
from app.routers.auth import get_password_hash


def load_seed_users() -> list[dict]:
    """Load user seed data from JSON fixture."""
    seed_file = Path(__file__).parent.parent.parent / "storage" / "seed_users.json"
    if not seed_file.exists():
        return []
    
    with open(seed_file, "r") as f:
        return json.load(f)


def seed_users() -> int:
    """
    Load seed users from JSON fixture into database.
    Returns the number of users created (not including existing users).
    """
    users_data = load_seed_users()
    if not users_data:
        return 0
    
    created_count = 0
    with Session(engine) as session:
        for user_data in users_data:
            # Check if user already exists
            existing = session.exec(
                select(User).where(User.email == user_data["email"])
            ).first()
            
            if existing:
                # Update password for presentation purposes
                existing.password_hash = get_password_hash("pass123")
                existing.name = user_data["name"]
                existing.company = user_data["company"]
                existing.role = UserRole(user_data["role"])
                session.add(existing)
                created_count += 1
                continue
            
            # Create new user from fixture
            user = User(
                name=user_data["name"],
                email=user_data["email"],
                password_hash=get_password_hash("pass123"),
                role=UserRole(user_data["role"]),
                company=user_data["company"],
                country=user_data["country"],
                is_active=True,
            )
            session.add(user)
            created_count += 1
        
        if created_count > 0:
            session.commit()
    
    return created_count
