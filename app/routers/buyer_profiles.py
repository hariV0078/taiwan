"""
Buyer Profiles Router
Manages buyer profiles for waste material procurement preferences.
"""

import traceback
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlmodel import Session, select

from app.database import engine
from app.models.transaction import BuyerProfile
from app.models.user import User, UserRole
from app.routers.auth import get_current_user
from app.services.matcher import upsert_buyer_profile

router = APIRouter()


class BuyerProfileRequest(BaseModel):
    """Request to create or update buyer profile."""
    material_needs: str  # e.g., "aluminum, copper, plastic"
    accepted_grades: str  # e.g., "A1,A2,B1"
    accepted_countries: str  # e.g., "ALL" or "India,Germany,Taiwan"
    max_price_per_kg: float  # Buyer's ceiling price for ALL materials
    min_quantity_kg: float  # Minimum quantity per transaction
    max_quantity_kg: float  # Maximum quantity per transaction

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "material_needs": "aluminum, copper, plastic",
                "accepted_grades": "A1,A2,B1,B2",
                "accepted_countries": "India,Germany,Taiwan,Brazil",
                "max_price_per_kg": 2.50,
                "min_quantity_kg": 100,
                "max_quantity_kg": 50000,
            }
        }
    )


class BuyerProfileResponse(BaseModel):
    """Response with buyer profile details."""
    id: uuid.UUID
    buyer_id: uuid.UUID
    material_needs: str
    accepted_grades: str
    accepted_countries: str
    max_price_per_kg: float
    min_quantity_kg: float
    max_quantity_kg: float
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


@router.post("/", response_model=BuyerProfileResponse, status_code=status.HTTP_201_CREATED)
def create_buyer_profile(
    payload: BuyerProfileRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Create a buyer profile.
    
    Only buyers can create profiles. One profile per buyer.
    The profile stores the buyer's material preferences and max price ceiling.
    """
    if current_user.role != UserRole.buyer:
        raise HTTPException(status_code=403, detail="Only buyers can create profiles")

    try:
        with Session(engine) as session:
            # Check if profile already exists
            existing = session.exec(
                select(BuyerProfile).where(BuyerProfile.buyer_id == current_user.id)
            ).first()
            
            if existing:
                raise HTTPException(status_code=400, detail="Buyer profile already exists. Use PATCH to update.")

            # Create new profile
            profile = BuyerProfile(
                buyer_id=current_user.id,
                material_needs=payload.material_needs,
                accepted_grades=payload.accepted_grades,
                accepted_countries=payload.accepted_countries,
                max_price_per_kg=payload.max_price_per_kg,
                min_quantity_kg=payload.min_quantity_kg,
                max_quantity_kg=payload.max_quantity_kg,
            )
            session.add(profile)
            session.commit()
            session.refresh(profile)
            
            # Upsert to ChromaDB for semantic matching
            upsert_buyer_profile(profile, current_user)
            
            return profile
    except HTTPException:
        raise
    except Exception:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/me", response_model=BuyerProfileResponse, status_code=status.HTTP_200_OK)
def get_buyer_profile(
    current_user: User = Depends(get_current_user)
):
    """
    Get current buyer's profile.
    
    Only available to buyer role.
    """
    if current_user.role != UserRole.buyer:
        raise HTTPException(status_code=403, detail="Only buyers can view profiles")

    try:
        with Session(engine) as session:
            profile = session.exec(
                select(BuyerProfile).where(BuyerProfile.buyer_id == current_user.id)
            ).first()
            
            if not profile:
                raise HTTPException(status_code=404, detail="Buyer profile not found. Create one first.")
            
            return profile
    except HTTPException:
        raise
    except Exception:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal server error")


@router.patch("/me", response_model=BuyerProfileResponse, status_code=status.HTTP_200_OK)
def update_buyer_profile(
    payload: BuyerProfileRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Update current buyer's profile.
    
    Can update material needs, grades, countries, and prices.
    """
    if current_user.role != UserRole.buyer:
        raise HTTPException(status_code=403, detail="Only buyers can update profiles")

    try:
        with Session(engine) as session:
            profile = session.exec(
                select(BuyerProfile).where(BuyerProfile.buyer_id == current_user.id)
            ).first()
            
            if not profile:
                raise HTTPException(status_code=404, detail="Buyer profile not found. Create one first.")
            
            # Update fields
            profile.material_needs = payload.material_needs
            profile.accepted_grades = payload.accepted_grades
            profile.accepted_countries = payload.accepted_countries
            profile.max_price_per_kg = payload.max_price_per_kg
            profile.min_quantity_kg = payload.min_quantity_kg
            profile.max_quantity_kg = payload.max_quantity_kg
            profile.updated_at = datetime.utcnow()
            
            session.add(profile)
            session.commit()
            session.refresh(profile)
            
            # Update ChromaDB
            upsert_buyer_profile(profile, current_user)
            
            return profile
    except HTTPException:
        raise
    except Exception:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal server error")
