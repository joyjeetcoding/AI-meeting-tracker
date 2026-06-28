"""
FastAPI Application Entry Point
---------------------------------
- Registers all routers
- Creates DB tables on startup
- Ensures data directories exist
- Sets up CORS so Gradio can talk to FastAPI
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.models.database import create_db_and_tables
from app.config import settings
from app.routers import upload, meetings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Runs on startup and shutdown.
    Replaces the old @app.on_event("startup") pattern.
    """
    # ── Startup ──────────────────────────────────────────────
    print(f"[App] Starting in ENV={settings.ENV}")
    settings.ensure_dirs()          # creates data/ subdirectories
    create_db_and_tables()          # creates SQLite tables if not exist
    print("[App] Ready ✅")
    yield
    # ── Shutdown ─────────────────────────────────────────────
    print("[App] Shutting down")


app = FastAPI(
    title="AI Meeting Action Tracker",
    description="Upload meeting audio or text → AI extracts summary + action items",
    version="1.0.0",
    lifespan=lifespan,
)


# ── CORS ──────────────────────────────────────────────────────
# Required so Gradio (running on port 7860) can call
# FastAPI (running on port 8000) without browser blocking it
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # tighten this in production
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Routers ───────────────────────────────────────────────────
app.include_router(upload.router)
app.include_router(meetings.router)


# ── Health check routes ───────────────────────────────────────

@app.get("/")
async def root():
    return {
        "app": "AI Meeting Action Tracker",
        "env": settings.ENV,
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    return {"status": "ok", "env": settings.ENV}