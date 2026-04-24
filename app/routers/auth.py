import traceback
import uuid
from datetime import datetime, timedelta

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


def create_access_token(user_id: uuid.UUID, role: UserRole) -> str:
    """Create a JWT token for the user."""
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "role": role.value, "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def get_current_user(request: Request, token: str | None = Depends(oauth2_scheme)) -> User:
    """Extract and validate the JWT token, return the user."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )

    # Check for test role header first (for development/testing)
    requested_role = request.headers.get("x-test-role")
    if requested_role:
        requested_role = requested_role.strip().lower()
        try:
            role = UserRole(requested_role)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid x-test-role. Use manufacturer, buyer, tpqc, or admin",
            ) from exc

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
            return user

    # If AUTH_BYPASS is enabled and no x-test-role header, create default admin user
    if settings.AUTH_BYPASS:
        email = f"test-admin@local"
        with Session(engine) as session:
            user = session.exec(select(User).where(User.email == email)).first()
            if not user:
                user = User(
                    name="Test Admin",
                    email=email,
                    password_hash="",
                    role=UserRole.admin,
                    company=settings.TEST_USER_COMPANY,
                    country=settings.TEST_USER_COUNTRY,
                    is_active=True,
                )
                session.add(user)
                session.commit()
                session.refresh(user)
            return user

    if not token:
        raise credentials_exception

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise credentials_exception
    except JWTError as exc:
        raise credentials_exception from exc

    with Session(engine) as session:
        user = session.get(User, uuid.UUID(user_id))
        if not user:
            raise credentials_exception
        return user


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
