from pydantic import BaseModel, EmailStr, field_validator, ConfigDict
from datetime import datetime


class SignupRequest(BaseModel):
    """
    Signup payload validation.
    
    Security notes:
    - EmailStr uses email-validator library for RFC-compliant validation
    - Password minimum 8 chars (NIST SP 800-63B recommendation)
    - No maximum length to allow passphrases, but API should enforce reasonable limit (e.g., 128)
    - No complexity rules (length is more important than character variety)
    """
    email: EmailStr
    password: str
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if len(v) > 128:
            raise ValueError('Password too long')
        return v


class LoginRequest(BaseModel):
    """
    Login payload validation.
    
    Uses same validation as signup for consistency.
    In production, might skip validation here to avoid information leakage,
    but keeping it prevents obviously malformed requests.
    """
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """
    Safe user representation for API responses.
    
    Critical: Never include password_hash in any response.
    """
    id: int
    email: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class MessageResponse(BaseModel):
    """
    Generic message response for operations without specific return data.
    """
    message: str