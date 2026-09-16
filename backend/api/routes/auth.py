"""Authentication endpoints: register, login, and profile management."""

from fastapi import APIRouter, Depends, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from api.deps import get_current_user
from config import get_settings
from models.database import User, get_db
from models.schemas import LoginRequest, TokenResponse, UserCreate, UserResponse
from services.auth_service import authenticate_user, create_access_token, create_user
from utils.rate_limit import limiter

settings = get_settings()
router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.RATE_LIMIT_AUTH)
def register(request: Request, user_data: UserCreate, db: Session = Depends(get_db)):
    return create_user(db, user_data)


@router.post("/login", response_model=TokenResponse)
@limiter.limit(settings.RATE_LIMIT_AUTH)
def login(request: Request, login_data: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate and return a JWT. Clients send it back as
    `Authorization: Bearer <token>` on subsequent requests."""
    user = authenticate_user(db, login_data.email, login_data.password)
    token = create_access_token({"sub": user.id, "email": user.email, "role": user.role})
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/login/form", response_model=TokenResponse, include_in_schema=False)
@limiter.limit(settings.RATE_LIMIT_AUTH)
def login_form(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """OAuth2 form login, used only by the Swagger UI's "Authorize" button."""
    user = authenticate_user(db, form_data.username, form_data.password)
    token = create_access_token({"sub": user.id, "email": user.email, "role": user.role})
    return TokenResponse(
        access_token=token, token_type="bearer", expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.get("/me", response_model=UserResponse)
def get_profile(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/me", response_model=UserResponse)
def update_profile(
    full_name: str = None,
    company: str = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if full_name:
        current_user.full_name = full_name
    if company:
        current_user.company = company
    db.commit()
    db.refresh(current_user)
    return current_user
