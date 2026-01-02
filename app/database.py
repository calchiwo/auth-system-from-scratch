from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import get_settings

settings = get_settings()

# Create engine with appropriate settings
# check_same_thread=False needed for SQLite with FastAPI
# For production Postgres, use connection pooling parameters
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
    echo=settings.debug
)

# Session factory for database operations
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for all models
Base = declarative_base()


def get_db():
    """
    Dependency that provides database session to route handlers.
    Ensures session is properly closed after request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize database schema.
    Creates all tables defined in models.
    Call this on application startup.
    """
    Base.metadata.create_all(bind=engine)