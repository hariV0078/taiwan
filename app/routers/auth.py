import traceback
import uuid
from datetime import datetime, timedelta
from typing import Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel, ConfigDict, EmailStr
from sqlmodel import Session, select

from app.config import get_settings
from app.database import engine
from app.models.user import User, UserRole

try:
    from supabase import create_client
except ImportError:
    create_client = None

router = APIRouter()
settings = get_settings()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/oauth/callback", auto_error=False)

# Initialize Supabase client if credentials are available
supabase_client = None
if settings.SUPABASE_URL and settings.SUPABASE_KEY:
    if create_client:
        try:
            supabase_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        except Exception:
            # Do not fail app startup for OAuth misconfiguration.
            supabase_client = None


class UserRegisterRequest(BaseModel):
    """Frontend user registration request (for non-OAuth user creation)."""
    email: EmailStr
    name: str
    company: str
    country: str
    role: UserRole
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "john@company.com",
                "name": "John Doe",
                "company": "Recycling Co",
                "country": "IN",
                "role": "manufacturer"
            }
        }
    )


class OAuth2LoginRequest(BaseModel):
    provider: str  # 'google', 'github', etc.
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {"provider": "google"}
        }
    )


class OAuth2CallbackRequest(BaseModel):
    access_token: str
    refresh_token: str
    user: dict  # Contains {id, email, user_metadata, etc.}
    role: UserRole
    company: str
    country: str
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "eyJhbGc...",
                "refresh_token": "eyJhbGc...",
                "user": {
                    "id": "user-uuid",
                    "email": "user@example.com",
                    "user_metadata": {"name": "John Doe"}
                },
                "role": "manufacturer",
                "company": "Company Ltd",
                "country": "IN"
            }
        }
    )


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    role: UserRole
    company: str
    country: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


def create_access_token(user_id: uuid.UUID, role: UserRole) -> str:
    """Create a JWT token for the user."""
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "role": role.value, "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def _detach_user(user: User) -> User:
    """Return a standalone User object that is safe outside DB session scope."""
    return User(
        id=user.id,
        name=user.name,
        email=user.email,
        password_hash=user.password_hash,
        role=user.role,
        company=user.company,
        country=user.country,
        created_at=user.created_at,
        is_active=user.is_active,
    )


def get_current_user(request: Request, token: Optional[str] = Depends(oauth2_scheme)) -> User:
    """
    DEVELOPMENT ONLY: Auth is disabled. Always returns a test user based on x-test-role header or defaults to admin.
    """
    # Get role from header or default to admin
    requested_role = (request.headers.get("x-test-role") or "admin").strip().lower()
    try:
        role = UserRole(requested_role)
    except ValueError:
        role = UserRole.admin

    email = f"test-{role.value}@local"
    with Session(engine) as session:
        user = session.exec(select(User).where(User.email == email)).first()
        if not user:
            user = User(
                name=f"Test {role.value.title()}",
                email=email,
                password_hash="",
                role=role,
                company=settings.TEST_USER_COMPANY,
                country=settings.TEST_USER_COUNTRY,
                is_active=True,
            )
            session.add(user)
            session.commit()
            session.refresh(user)
        return _detach_user(user)


@router.post("/oauth/login")
def oauth_login(payload: OAuth2LoginRequest):
    """
    Initiate OAuth flow. Returns the Supabase OAuth URL.
    Client redirects user to this URL, then Supabase redirects back to /auth/oauth/callback.
    """
    if not supabase_client:
        raise HTTPException(status_code=500, detail="Supabase not configured")
    
    try:
        # Get the OAuth URL for the provider
        response = supabase_client.auth.sign_in_with_oauth({
            "provider": payload.provider,
            "options": {
                "redirect_to": f"{settings.SUPABASE_URL}/oauth/callback"  # Frontend URL
            }
        })
        return {"url": response.get("url", "")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OAuth error: {str(e)}")


@router.post("/oauth/callback", response_model=TokenResponse, status_code=status.HTTP_200_OK)
def oauth_callback(payload: OAuth2CallbackRequest):
    """
    Handle OAuth callback from Supabase.
    Creates or updates user in our DB and returns JWT token.
    """
    if not supabase_client:
        raise HTTPException(status_code=500, detail="Supabase not configured")
    
    try:
        # Extract user info from Supabase auth response
        supabase_user_id = payload.user.get("id")
        email = payload.user.get("email")
        name = payload.user.get("user_metadata", {}).get("name", email.split("@")[0])
        
        if not supabase_user_id or not email:
            raise HTTPException(status_code=400, detail="Invalid OAuth response")
        
        with Session(engine) as session:
            # Check if user already exists
            user = session.exec(select(User).where(User.email == email)).first()
            
            if not user:
                # Create new user from OAuth
                user = User(
                    id=uuid.UUID(supabase_user_id),
                    name=name,
                    email=email,
                    password_hash="",  # OAuth users don't have passwords
                    role=payload.role,
                    company=payload.company,
                    country=payload.country,
                    is_active=True,
                )
                session.add(user)
            else:
                # Update user if needed
                user.name = name
                user.role = payload.role
                user.company = payload.company
                user.country = payload.country
                
            session.commit()
            session.refresh(user)
            
            # Create JWT token for our app
            token = create_access_token(user.id, user.role)
            return TokenResponse(access_token=token)
            
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error processing OAuth: {str(e)}")


@router.get("/me", response_model=UserOut, status_code=status.HTTP_200_OK)
def me(current_user: User = Depends(get_current_user)):
    """Return the current authenticated user profile."""
    return UserOut.model_validate(current_user)


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: UserRegisterRequest):
    """
    Register a new user via frontend form (non-OAuth).
    Frontend can use this to create users directly without OAuth.
    Returns the created user profile.
    """
    with Session(engine) as session:
        # Check if user already exists
        existing_user = session.exec(select(User).where(User.email == payload.email)).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"User with email {payload.email} already exists"
            )
        
        # Create new user
        user = User(
            name=payload.name,
            email=payload.email,
            password_hash="",  # Direct registration users don't have passwords
            role=payload.role,
            company=payload.company,
            country=payload.country,
            is_active=True,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        
        return UserOut.model_validate(user)
