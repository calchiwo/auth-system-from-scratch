from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """
    Application configuration loaded from environment variables.
    Uses pydantic for validation and type safety.
    """
    environment: str = "development"
    debug: bool = True
    
    # Session secret must be cryptographically random and kept secure
    # Changing this invalidates all existing sessions
    session_secret_key: str
    
    database_url: str = "sqlite:///./auth.db"
    
    # Session lifetime in hours
    session_expire_hours: int = 24
    
    # Cookie security settings
    # secure=True enforces HTTPS only - must be True in production
    cookie_secure: bool = False
    cookie_domain: str = "localhost"
    
    # HTTP-only prevents JavaScript access - always True for security
    cookie_httponly: bool = True
    
    # Lax allows cookie on normal navigation but blocks on CSRF-prone requests
    cookie_samesite: str = "lax"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    """
    Cached settings instance. Load once, reuse throughout application lifecycle.
    """
    return Settings()