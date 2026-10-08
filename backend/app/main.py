from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings

app = FastAPI(
    title="AI Customer Support Agent API",
    description="Backend API for AI Customer Support Agent (Educational & Production-Minded Architecture)",
    version="0.1.0"
)

# CORS Middleware for Frontend Communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust allowed origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {
        "status": "healthy",
        "service": "AI Customer Support Agent API",
        "version": "0.1.0",
        "phase": "Phase 0 - Setup and Architecture"
    }

@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "environment": settings.APP_ENV
    }
