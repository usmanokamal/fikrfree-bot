"""
app/api_v1.py - RESTful API endpoints for FikrFree Assistant
"""

import asyncio
import time
from datetime import datetime
from typing import Optional

import bleach
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field

from app.bot import chat as bot_chat, detect_language
from app.session_manager import session_manager, SessionManager
from llama_index.core.base.llms.types import MessageRole
import json
import csv
import os

# API Router
api_v1_router = APIRouter(prefix="/api/v1", tags=["FikrFree Assistant API"])

# Request/Response Models
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000, description="User message")
    stream: bool = Field(default=False, description="Enable streaming response")

class ChatResponse(BaseModel):
    session_id: str
    response: str
    language_detected: str
    timestamp: str
    message_count: int

class StreamingChatResponse(BaseModel):
    session_id: str
    chunk: str
    type: str  # "content", "complete", "error"
    timestamp: str

class SessionCreateResponse(BaseModel):
    session_id: str
    status: str
    created_at: str

class SessionHistoryResponse(BaseModel):
    session_id: str
    messages: list
    message_count: int
    created_at: str
    last_activity: str

class ErrorResponse(BaseModel):
    error: str
    message: str
    timestamp: str

# Lead and Event models
class LeadRequest(BaseModel):
    consent: bool = Field(..., description="User consent to store details")
    name: Optional[str] = Field(default=None)
    age: Optional[int] = Field(default=None, ge=0, le=120)
    city: Optional[str] = Field(default=None)
    dependents: Optional[int] = Field(default=None, ge=0)
    budget_pkr: Optional[float] = Field(default=None, ge=0)
    intent: Optional[str] = Field(default=None, description="buy|renew|inquire|claims|other")
    product_interest: Optional[str] = Field(default=None)
    session_id: Optional[str] = Field(default=None)
    phone: Optional[str] = Field(default=None, description="Optional phone number")
    cnic: Optional[str] = Field(default=None, description="Optional Pakistani CNIC (13 digits)")

class EventLog(BaseModel):
    event: str
    session_id: Optional[str] = None
    metadata: Optional[dict] = None

# Helper Functions
def get_session_or_404(session_id: str):
    """Get session or raise 404 error."""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=404, 
            detail=f"Session {session_id} not found or expired"
        )
    return session

async def process_chat_message(session_id: str, message: str) -> tuple:
    """Process chat message and return response with metadata."""
    # Get session context
    session = get_session_or_404(session_id)
    context_messages = session.get_context_messages()
    
    # Detect language
    language = detect_language(message)
    
    # Add user message to session
    session_manager.add_message_to_session(session_id, MessageRole.USER, message)
    
    # Get bot response
    full_response = ""
    async for chunk in bot_chat(message):
        full_response += chunk
    
    # Add bot response to session
    session_manager.add_message_to_session(session_id, MessageRole.ASSISTANT, full_response)
    
    return full_response, language, len(session.messages)

# API Endpoints

@api_v1_router.get("/")
async def api_welcome():
    """API welcome endpoint for when people visit /api/v1 in browser"""
    return {
        "message": "🏥 Welcome to FikrFree Assistant API!",
        "version": "1.0",
        "description": "Intelligent healthcare chatbot with bilingual support (English/Roman Urdu)",
        "endpoints": {
            "health": "GET /api/v1/health - Check API health",
            "sessions": "POST /api/v1/sessions/start - Create new session",
            "chat": "POST /api/v1/sessions/{session_id}/chat - Send message",
            "history": "GET /api/v1/sessions/{session_id}/history - Get conversation history",
            "docs": "https://your-domain.com/docs - Interactive API documentation"
        },
        "quick_test": {
            "1": "Visit /api/v1/health to check API status",
            "2": "Visit /docs for interactive testing",
            "3": "POST to /api/v1/sessions/start to create a session"
        },
        "support": {
            "documentation": "/docs",
            "sdk_python": "Available - fikrfree_client_sdk.py",
            "sdk_javascript": "Available - fikrfree-client-sdk.js"
        }
    }

@api_v1_router.get("/health")
async def health_check():
    """API health check endpoint."""
    return {
        "status": "healthy",
        "service": "FikrFree Assistant API",
        "version": "1.0",
        "timestamp": datetime.now().isoformat(),
        "active_sessions": session_manager.get_active_session_count()
    }

@api_v1_router.post("/sessions/start", response_model=SessionCreateResponse)
async def create_session():
    """Create a new conversation session."""
    session_id = session_manager.create_session()
    session = session_manager.get_session(session_id)
    
    return SessionCreateResponse(
        session_id=session_id,
        status="active",
        created_at=session.created_at.isoformat()
    )

@api_v1_router.post("/sessions/{session_id}/chat")
async def chat_with_session(
    session_id: str, 
    request: ChatRequest, 
    http_request: Request
):
    """Send a message to a specific session and get response."""
    # Validate session exists
    get_session_or_404(session_id)
    
    # Clean and validate message
    clean_message = bleach.clean(request.message.strip())
    if not clean_message:
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    
    timestamp = datetime.now().isoformat()
    
    try:
        if request.stream:
            # Streaming response
            async def generate_stream():
                try:
                    session = get_session_or_404(session_id)
                    language = detect_language(clean_message)
                    
                    # Add user message to session
                    session_manager.add_message_to_session(session_id, MessageRole.USER, clean_message)
                    
                    full_response = ""
                    async for chunk in bot_chat(clean_message):
                        if await http_request.is_disconnected():
                            yield f"data: {{'type': 'error', 'message': 'Client disconnected'}}\n\n"
                            return
                        
                        full_response += chunk
                        chunk_data = {
                            "session_id": session_id,
                            "chunk": chunk,
                            "type": "content",
                            "timestamp": datetime.now().isoformat()
                        }
                        yield f"data: {chunk_data}\n\n"
                        await asyncio.sleep(0.01)
                    
                    # Add bot response to session
                    session_manager.add_message_to_session(session_id, MessageRole.ASSISTANT, full_response)
                    
                    # Send completion signal
                    complete_data = {
                        "session_id": session_id,
                        "type": "complete",
                        "full_response": full_response,
                        "language_detected": language,
                        "message_count": len(session.messages),
                        "timestamp": timestamp
                    }
                    yield f"data: {complete_data}\n\n"
                    
                except Exception as e:
                    error_data = {
                        "session_id": session_id,
                        "type": "error",
                        "message": str(e),
                        "timestamp": datetime.now().isoformat()
                    }
                    yield f"data: {error_data}\n\n"
            
            return StreamingResponse(
                generate_stream(),
                media_type="text/plain",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "Access-Control-Allow-Origin": "*",
                }
            )
        
        else:
            # Non-streaming response
            response_text, language, message_count = await process_chat_message(session_id, clean_message)
            
            return ChatResponse(
                session_id=session_id,
                response=response_text,
                language_detected=language,
                timestamp=timestamp,
                message_count=message_count
            )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat processing failed: {str(e)}")

@api_v1_router.get("/sessions/{session_id}/history", response_model=SessionHistoryResponse)
async def get_session_history(session_id: str):
    """Get conversation history for a session."""
    session = get_session_or_404(session_id)
    
    return SessionHistoryResponse(
        session_id=session_id,
        messages=session.to_dict()["messages"],
        message_count=len(session.messages),
        created_at=session.created_at.isoformat(),
        last_activity=session.last_activity.isoformat()
    )

@api_v1_router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a conversation session."""
    if session_manager.delete_session(session_id):
        return {
            "message": f"Session {session_id} deleted successfully",
            "timestamp": datetime.now().isoformat()
        }
    else:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

@api_v1_router.get("/sessions/{session_id}/info")
async def get_session_info(session_id: str):
    """Get basic information about a session."""
    session = get_session_or_404(session_id)
    
    return {
        "session_id": session_id,
        "created_at": session.created_at.isoformat(),
        "last_activity": session.last_activity.isoformat(),
        "message_count": len(session.messages),
        "is_active": True
    }

@api_v1_router.get("/sessions/stats")
async def get_sessions_stats():
    """Get statistics about all active sessions."""
    stats = session_manager.get_session_stats()
    return {
        **stats,
        "timestamp": datetime.now().isoformat()
    }

# Note: Exception handlers are added at the app level in main.py, not router level

@api_v1_router.post("/leads")
async def create_lead(lead: LeadRequest):
    """Store a structured lead in CSV with consent."""
    if not lead.consent:
        raise HTTPException(status_code=400, detail="Consent required to store lead")
    csv_file = "leads.csv"
    exists = os.path.isfile(csv_file)
    # Basic validations and masking
    def _digits(s: Optional[str]) -> str:
        return "".join(ch for ch in (s or "") if ch.isdigit())
    phone_digits = _digits(lead.phone) if lead.phone else ""
    if phone_digits and len(phone_digits) < 10:
        raise HTTPException(status_code=400, detail="Phone seems invalid")
    cnic_digits = _digits(lead.cnic) if lead.cnic else ""
    masked_cnic = ""
    if cnic_digits:
        if len(cnic_digits) != 13:
            raise HTTPException(status_code=400, detail="CNIC must be 13 digits")
        masked_cnic = f"{cnic_digits[:5]}-{cnic_digits[5:12]}-{cnic_digits[12:]}"
        # Mask middle 7 digits
        masked_cnic = masked_cnic.replace(cnic_digits[5:12], "*******")

    data = {
        "timestamp": datetime.now().isoformat(),
        "name": lead.name or "",
        "age": lead.age if lead.age is not None else "",
        "city": lead.city or "",
        "dependents": lead.dependents if lead.dependents is not None else "",
        "budget_pkr": lead.budget_pkr if lead.budget_pkr is not None else "",
        "intent": (lead.intent or "").lower(),
        "product_interest": lead.product_interest or "",
        "session_id": lead.session_id or "",
        "phone": phone_digits or "",
        "cnic_masked": masked_cnic or "",
    }
    with open(csv_file, "a", newline="", encoding="utf-8") as f:
        fieldnames = list(data.keys())
        w = csv.DictWriter(f, fieldnames=fieldnames)
        if not exists:
            w.writeheader()
        w.writerow(data)
    return {"status": "success", "message": "Lead stored", **data}

@api_v1_router.post("/events")
async def log_event(event: EventLog):
    """Log KPI/guardrail events to a CSV (simple analytics)."""
    csv_file = "events.csv"
    exists = os.path.isfile(csv_file)
    data = {
        "timestamp": datetime.now().isoformat(),
        "event": event.event,
        "session_id": event.session_id or "",
        "metadata": (event.metadata or {}),
    }
    with open(csv_file, "a", newline="", encoding="utf-8") as f:
        fieldnames = ["timestamp", "event", "session_id", "metadata"]
        w = csv.DictWriter(f, fieldnames=fieldnames)
        if not exists:
            w.writeheader()
        # Serialize metadata as JSON string
        row = dict(data)
        row["metadata"] = json.dumps(row["metadata"], ensure_ascii=False)
        w.writerow(row)
    return {"status": "success", "message": "Event logged"}
