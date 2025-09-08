# app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from app.index_generator import generate_indexes, init_indexes
from app.index_listener import start_listener
from typing import Dict
from app.api import router as api_router
from app.api_v1 import api_v1_router
from llama_index.core import VectorStoreIndex
import cProfile
import pstats
import io
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

# --- CSP Imports ---
from starlette.middleware.base import BaseHTTPMiddleware
# -------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_indexes()
    yield
    # Shutdown (if needed)

app = FastAPI(
    title="FikrFree Assistant API",
    description="Intelligent healthcare and insurance chatbot API with bilingual support (English/Roman Urdu)",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)
indexes: Dict[str, VectorStoreIndex] = {}

# --- Content Security Policy Middleware ---
CSP_POLICY = (
    "default-src 'self'; "
    "script-src 'self' https://code.jquery.com https://cdn.jsdelivr.net 'unsafe-inline'; "
    "style-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
    "img-src 'self' data: https://fastapi.tiangolo.com; "
    "font-src 'self';"
)


class CSPMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["Content-Security-Policy"] = CSP_POLICY
        return response

app.add_middleware(CSPMiddleware)
# ------------------------------------------

# Allow requests from your React application's domain and API consumers
origins = [
    "http://10.173.2.223:9991",
    "http://localhost:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "*"  # Allow all origins for API testing - restrict this in production
]

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Mount static files (CSS, JS, images)
app.mount("/static", StaticFiles(directory="static"), name="static")
# Setup Jinja2 template directory
templates = Jinja2Templates(directory="templates")

# Serve Frontend (index.html)
@app.get("/", response_class=HTMLResponse)
async def serve_frontend(request: Request):
    # Serves your chatbot UI at root URL
    return templates.TemplateResponse("index.html", {"request": request})

app.include_router(api_router)
app.include_router(api_v1_router)
