from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import settings
from app.database import engine, Base
from app.models import (
    Customer,
    Product,
    Order,
    OrderItem,
    Shipment,
    Return,
    Refund,
    SupportTicket,
)
from app.api.auth import router as auth_router
from app.api.chat import router as chat_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure database tables exist
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as exc:
        print(f"[Warning] Could not initialize database tables on startup: {exc}")
    yield
    # Shutdown logic if needed

app = FastAPI(
    title="AI Customer Support Agent API",
    description="Backend API for AI Customer Support Agent (Educational & Production-Minded Architecture)",
    version="0.5.0",
    lifespan=lifespan
)

# CORS Middleware for Frontend Communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API Routers
app.include_router(auth_router)
app.include_router(chat_router)

@app.get("/", tags=["General"])
def read_root():
    return {
        "status": "healthy",
        "service": "AI Customer Support Agent API",
        "version": "0.5.0",
        "phase": "Phase 5 - Router Agent (LangGraph Intent Classification)"
    }

@app.get("/health", tags=["General"])
def health_check():
    db_status = "connected"
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        db_status = f"unavailable: {str(exc)}"

    return {
        "status": "ok",
        "environment": settings.APP_ENV,
        "database": db_status
    }
