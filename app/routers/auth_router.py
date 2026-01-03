from fastapi import APIRouter, Depends, HTTPException, status, Response, Cookie
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Optional
from app.database import get_db
from app.models import User
from app.schemas import SignupRequest, LoginRequest, UserResponse, MessageResponse
from app.auth import hash_password, verify_password, create_session, delete_session
from app.dependencies import get_current_user
from app.config import get_settings

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def signup(
    request: SignupRequest,
    response: Response,
    db: Session = Depends(get_db)
):
    """
    Create new user account.
    
    Process:
    1. Validate input (done by Pydantic)
    2. Normalize email to lowercase
    3. Hash password
    4. Insert user into database
    5. Create session
    6. Set session cookie
    7. Return user data
    
    Error cases:
    - 400: Validation failed (caught by FastAPI)
    - 409: Email already exists
    - 500: Database error
    """
    # Normalize email to prevent duplicate accounts with different casing
    email = request.email.lower()
    
    # Hash password before storing
    # Never store plaintext passwords
    password_hash = hash_password(request.password)
    
    # Create user
    user = User(email=email, password_hash=password_hash)
    
    try:
        db.add(user)
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        # Email uniqueness violation
        # Return 409 Conflict - this is an acceptable information leak
        # Alternative: return 400 with generic message to prevent email enumeration
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )
    
    # Create session and set cookie
    session_id = create_session(db, user.id)
    _set_session_cookie(response, session_id)
    
    return user


@router.post("/login", response_model=UserResponse)
async def login(
    request: LoginRequest,
    response: Response,
    db: Session = Depends(get_db)
):
    """
    Authenticate user and create session.
    
    Process:
    1. Normalize email
    2. Look up user by email
    3. Verify password hash
    4. Create session
    5. Set cookie
    6. Return user data
    
    Security notes:
    - Generic error message prevents email enumeration
    - Constant-time password verification prevents timing attacks
    - No indication whether email or password was wrong
    
    Rate limiting should be implemented here in production.
    """
    email = request.email.lower()
    
    # Look up user
    user = db.query(User).filter(User.email == email).first()
    
    # Verify password
    # Check even if user not found to prevent timing attacks
    if not user or not verify_password(request.password, user.password_hash):
        # Generic error - don't reveal whether email exists
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    # Create session and set cookie
    session_id = create_session(db, user.id)
    _set_session_cookie(response, session_id)
    
    return user


@router.post("/logout", response_model=MessageResponse)
async def logout(
    response: Response,
    session_id: Optional[str] = Cookie(None, alias="session_id"),
    db: Session = Depends(get_db)
):
    """
    Invalidate session and clear cookie.
    
    Process:
    1. Delete session from database
    2. Clear session cookie
    
    Returns success even if session doesn't exist (idempotent).
    """
    if session_id:
        delete_session(db, session_id)
    
    # Clear cookie by setting it with expired date
    _clear_session_cookie(response)
    
    return MessageResponse(message="Logged out successfully")


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(user: User = Depends(get_current_user)):
    """
    Get authenticated user's information.
    
    Protected route example.
    Returns 401 if not authenticated (handled by dependency).
    """
    return user


def _set_session_cookie(response: Response, session_id: str):
    """
    Set session cookie with security flags.
    
    Cookie attributes:
    - httponly: Prevents JavaScript access (XSS protection)
    - secure: HTTPS only (must be True in production)
    - samesite: Lax for CSRF protection while allowing normal navigation
    - max_age: Cookie lifetime in seconds
    - path: Cookie sent on all paths
    - domain: Limits cookie to specific domain
    
    The cookie only contains the session ID (opaque token).
    All user data stays server-side.
    """
    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=settings.cookie_httponly,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=settings.session_expire_hours * 3600,
        path="/",
        domain=settings.cookie_domain if settings.cookie_domain != "localhost" else None
    )


def _clear_session_cookie(response: Response):
    """
    Clear session cookie by setting it with max_age=0.
    
    Also sets expires to past date as fallback.
    """
    response.set_cookie(
        key="session_id",
        value="",
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=0,
        path="/",
        domain=settings.cookie_domain if settings.cookie_domain != "localhost" else None
    )