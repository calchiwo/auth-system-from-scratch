from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.database import init_db
from app.routers import auth_router
from app.dependencies import get_current_user
from app.models import User
from app.config import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    Runs on startup and shutdown.
    """
    # Startup: Initialize database
    init_db()
    yield
    # Shutdown: Cleanup if needed


app = FastAPI(
    title="Auth System",
    description="Production authentication system built from scratch",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
# In production, restrict origins to your frontend domain
# Example: origins = ["https://yourdomain.com"]
if settings.debug:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Restrict in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Register routers
app.include_router(auth_router.router)


@app.get("/")
async def root():
    """
    Health check endpoint.
    """
    return {
        "status": "running",
        "version": "1.0.0"
    }


@app.get("/protected")
async def protected_route(user: User = Depends(get_current_user)):
    """
    Example protected route.
    
    Requires authentication via get_current_user dependency.
    Returns 401 if not authenticated.
    """
    return {
        "message": "This is a protected route",
        "user_id": user.id,
        "user_email": user.email
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )