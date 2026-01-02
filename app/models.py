from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index
from sqlalchemy.sql import func
from app.database import Base
import uuid


class User(Base):
    """
    Core user model. Stores credentials and metadata.
    
    Design notes:
    - email is unique and indexed for fast lookup
    - password_hash never leaves the database layer
    - created_at for auditing and analytics
    - Integer ID for simplicity; UUID alternative shown in comment
    """
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    # Alternative: id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    def __repr__(self):
        return f"<User(id={self.id}, email={self.email})>"


class Session(Base):
    """
    Server-side session storage.
    
    Design notes:
    - session_id is the token stored in cookie (32 random bytes, hex encoded)
    - user_id foreign key for fast user lookup and cascade deletion
    - expires_at indexed for efficient cleanup queries
    - created_at for session duration analytics
    
    Session lifecycle:
    1. Created on login with random session_id
    2. Validated on each request against expires_at
    3. Deleted on logout or expiration
    """
    __tablename__ = "sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(64), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    
    # Composite index for common query pattern: lookup by session_id and check expiration
    __table_args__ = (
        Index('ix_session_lookup', 'session_id', 'expires_at'),
    )
    
    def __repr__(self):
        return f"<Session(id={self.id}, user_id={self.user_id})>"ssss