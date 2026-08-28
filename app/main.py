"""
ArogyaMitra Application Entry Point
Source of truth: systemdesign.md Section 17 & brandguideline.md
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from jinja2 import Environment, FileSystemLoader

from app.config import BASE_DIR, DATA_DIR, UPLOAD_DIR
from app.db import init_db
from app.routes import auth, patient, intake, documents, doctor, lab, radiology, abdm, admin, export

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize SQLite tables and seed data on startup
    init_db()
    yield

app = FastAPI(
    title="ArogyaMitra Pre-Consultation Clinical Intake Platform",
    description="Multilingual AI-powered clinical history, OCR document digitization, and physician summary platform.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for open accessibility across local networks
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static and Data Directories
STATIC_DIR = BASE_DIR / "app" / "static"
TEMPLATES_DIR = BASE_DIR / "app" / "templates"

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.mount("/data/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

# Include API Routers
app.include_router(auth.router)
app.include_router(patient.router)
app.include_router(intake.router)
app.include_router(documents.router)
app.include_router(doctor.router)
app.include_router(radiology.router)
app.include_router(lab.router)
app.include_router(abdm.router)
app.include_router(admin.router)
app.include_router(export.router)

# Template Engine
jinja_env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))

@app.get("/", response_class=HTMLResponse)
def index_view(request: Request):
    """Serves the unified responsive web & kiosk interface."""
    template = jinja_env.get_template("index.html")
    return template.render(request=request)

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "platform": "ArogyaMitra",
        "mode": "Hackathon Ready",
        "mock_abdm": True
    }
