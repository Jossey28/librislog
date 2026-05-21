"""Authentication endpoints — login, logout, setup, session, and CSRF."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlmodel import Session, select

from app.auth import (
    clear_browser_session,
    ensure_password_complexity,
    get_password_hash,
    require_user,
    start_browser_session,
    verify_password,
)
from app.database import get_session
from app.models import User, UserRole, UserSettings
from app.schemas import SetupRequest, UserLogin, UserRead

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/setup-required")
def setup_required(session: Session = Depends(get_session)) -> dict:
    """Return whether initial admin setup is required."""
    admin = session.exec(select(User).where(User.role == UserRole.admin).limit(1)).first()
    return {"required": admin is None}


@router.post("/setup")
def setup(
    request: SetupRequest,
    http_request: Request,
    session: Session = Depends(get_session),
) -> dict:
    """Perform initial admin setup (creates the first admin user)."""
    admin_exists = session.exec(select(User).where(User.role == UserRole.admin).limit(1)).first()
    if admin_exists:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Setup already completed")

    existing_email = session.exec(select(User).where(User.email == request.email)).first()
    if existing_email:
        raise HTTPException(status_code=400, detail="Email already registered")

    ensure_password_complexity(request.password)

    user = User(
        firstname=request.firstname,
        lastname=request.lastname,
        email=request.email,
        role=UserRole.admin,
        hashed_password=get_password_hash(request.password),
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    session.add(UserSettings(user_id=user.id, language="en"))
    session.commit()

    start_browser_session(http_request, user.id)
    return {"user": UserRead.model_validate(user)}


@router.post("/login")
def login(
    credentials: UserLogin,
    http_request: Request,
    session: Session = Depends(get_session),
) -> dict:
    """Authenticate with email and password, starting a browser session."""
    user = session.exec(select(User).where(User.email == credentials.email)).first()
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")

    start_browser_session(http_request, user.id)
    return {"user": UserRead.model_validate(user)}


@router.post("/logout")
def logout(http_request: Request) -> dict:
    """Clear the browser session."""
    clear_browser_session(http_request)
    return {"message": "Logged out"}


@router.get("/me", response_model=UserRead)
def me(current_user: User = Depends(require_user)) -> User:
    """Return the currently authenticated user."""
    return current_user


@router.get("/csrf")
def csrf_token(request: Request) -> dict:
    """Return the current CSRF token from the browser session."""
    token = request.session.get("csrf_token")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return {"csrf_token": token}
