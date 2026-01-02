from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """
    Application configuration loaded from environment variables.
    Uses pydantic for validation and type safety.
    """
    environment: str = "development"
    debug: bool = True
    
    session_secret_key: str
    
    database_url: str = "sqlite:///./auth.db"
    
    session_expire_hours: int = 24
    
    cookie_secure: bool = False
    cookie_domain: str = "localhost"
    
    cookie_httponly: bool = True
    
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