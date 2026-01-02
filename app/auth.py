from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHashError
import secrets
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from app.models import User, Session as SessionModel
from app.config import get_settings

settings = get_settings()

# Argon2 hasher with secure defaults
# Argon2id is recommended variant (combines Argon2i and Argon2d)
# Memory cost, time cost, and parallelism are automatically tuned
ph = PasswordHasher()


def hash_password(password: str) -> str:
    """
    Hash password using Argon2id.
    
    Argon2 advantages:
    - Winner of Password Hashing Competition (2015)
    - Memory-hard: Resists GPU/ASIC attacks
    - Configurable cost parameters
    - Automatic salt generation
    
    Returns hash string that includes algorithm parameters and salt.
    Format: $argon2id$v=19$m=65536,t=3,p=4$salt$hash
    """
    return ph.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """
    Verify password against stored hash.
    
    Uses constant-time comparison internally to prevent timing attacks.
    Returns False for any error to avoid information leakage.
    """
    try:
        ph.verify(password_hash, password)
        
        # Check if hash needs rehashing (parameters changed)
        # In production, update user's hash if this returns True
        if ph.check_needs_rehash(password_hash):
            # Rehashing logic would go here in a full implementation
            pass
        
        return True
    except (VerifyMismatchError, InvalidHashError):
        return False


def generate_session_id() -> str:
    """
    Generate cryptographically secure session identifier.
    
    Uses 32 bytes (256 bits) of randomness.
    Hex encoded = 64 character string.
    
    Why not UUID?
    - UUIDs have version bits that reduce entropy
    - secrets.token_hex() is explicitly for security tokens
    """
    return secrets.token_hex(32)


def create_session(db: Session, user_id: int) -> str:
    """
    Create new session for user.
    
    Returns session_id to be stored in cookie.
    Session expires after configured duration.
    """
    session_id = generate_session_id()
    expires_at = datetime.utcnow() + timedelta(hours=settings.session_expire_hours)
    
    session = SessionModel(
        session_id=session_id,
        user_id=user_id,
        expires_at=expires_at
    )
    
    db.add(session)
    db.commit()
    
    return session_id


def get_user_from_session(db: Session, session_id: str) -> Optional[User]:
    """
    Validate session and retrieve associated user.
    
    Returns None if:
    - Session doesn't exist
    - Session is expired
    - User doesn't exist (shouldn't happen with FK constraint)
    
    Note: This queries on every authenticated request.
    In high-traffic scenarios, cache user objects in Redis.
    """
    session = db.query(SessionModel).filter(
        SessionModel.session_id == session_id,
        SessionModel.expires_at > datetime.utcnow()
    ).first()
    
    if not session:
        return None
    
    user = db.query(User).filter(User.id == session.user_id).first()
    return user


def delete_session(db: Session, session_id: str) -> bool:
    """
    Delete session (logout).
    
    Returns True if session was deleted, False if not found.
    """
    result = db.query(SessionModel).filter(
        SessionModel.session_id == session_id
    ).delete()
    
    db.commit()
    return result > 0


def delete_user_sessions(db: Session, user_id: int) -> int:
    """
    Delete all sessions for a user.
    
    Useful for:
    - Password change (invalidate all sessions)
    - Account suspension
    - "logout all devices" feature
    
    Returns number of sessions deleted.
    """
    result = db.query(SessionModel).filter(
        SessionModel.user_id == user_id
    ).delete()
    
    db.commit()
    return result


def cleanup_expired_sessions(db: Session) -> int:
    """
    Remove expired sessions from database.
    
    Should be called periodically via background task.
    Returns number of sessions cleaned up.
    """
    result = db.query(SessionModel).filter(
        SessionModel.expires_at <= datetime.utcnow()
    ).delete()
    
    db.commit()
    return resultss