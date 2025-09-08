"""
app/session_manager.py - Session-based conversation management for API
"""

import uuid
import time
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from llama_index.core.base.llms.types import ChatMessage, MessageRole

@dataclass
class ChatSession:
    """Represents a conversation session with context and metadata."""
    session_id: str
    created_at: datetime
    last_activity: datetime
    messages: List[ChatMessage] = field(default_factory=list)
    max_messages: int = 20
    max_history_length: int = 2000
    
    def add_message(self, role: MessageRole, content: str) -> None:
        """Add a message to the session history."""
        message = ChatMessage(role=role, content=content)
        self.messages.append(message)
        self.last_activity = datetime.now()
        
        # Trim history if too long
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages:]
    
    def get_context_messages(self) -> List[ChatMessage]:
        """Get recent messages for context (last 8 messages for memory)."""
        return self.messages[-8:] if len(self.messages) > 8 else self.messages
    
    def is_expired(self, timeout_hours: int = 24) -> bool:
        """Check if session has expired."""
        expiry_time = self.last_activity + timedelta(hours=timeout_hours)
        return datetime.now() > expiry_time
    
    def to_dict(self) -> dict:
        """Convert session to dictionary for API responses."""
        return {
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "message_count": len(self.messages),
            "messages": [
                {
                    "role": msg.role.value,
                    "content": msg.content,
                    "timestamp": self.last_activity.isoformat()  # Simplified timestamp
                }
                for msg in self.messages
            ]
        }

class SessionManager:
    """Manages multiple chat sessions for API users."""
    
    def __init__(self):
        self.sessions: Dict[str, ChatSession] = {}
        self.cleanup_interval = 3600  # Cleanup every hour
        self.last_cleanup = time.time()
    
    def create_session(self) -> str:
        """Create a new chat session and return session ID."""
        session_id = str(uuid.uuid4())
        now = datetime.now()
        
        session = ChatSession(
            session_id=session_id,
            created_at=now,
            last_activity=now
        )
        
        self.sessions[session_id] = session
        self._cleanup_expired_sessions()
        
        return session_id
    
    def get_session(self, session_id: str) -> Optional[ChatSession]:
        """Get a session by ID."""
        session = self.sessions.get(session_id)
        if session and session.is_expired():
            # Remove expired session
            del self.sessions[session_id]
            return None
        return session
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False
    
    def add_message_to_session(self, session_id: str, role: MessageRole, content: str) -> bool:
        """Add a message to a specific session."""
        session = self.get_session(session_id)
        if session:
            session.add_message(role, content)
            return True
        return False
    
    def get_session_context(self, session_id: str) -> Optional[List[ChatMessage]]:
        """Get conversation context for a session."""
        session = self.get_session(session_id)
        if session:
            return session.get_context_messages()
        return None
    
    def _cleanup_expired_sessions(self) -> None:
        """Remove expired sessions to free memory."""
        current_time = time.time()
        if current_time - self.last_cleanup < self.cleanup_interval:
            return
        
        expired_sessions = [
            sid for sid, session in self.sessions.items()
            if session.is_expired()
        ]
        
        for sid in expired_sessions:
            del self.sessions[sid]
        
        self.last_cleanup = current_time
        
        if expired_sessions:
            print(f"[SessionManager] Cleaned up {len(expired_sessions)} expired sessions")
    
    def get_active_session_count(self) -> int:
        """Get number of active sessions."""
        self._cleanup_expired_sessions()
        return len(self.sessions)
    
    def get_session_stats(self) -> dict:
        """Get statistics about active sessions."""
        self._cleanup_expired_sessions()
        return {
            "active_sessions": len(self.sessions),
            "total_messages": sum(len(session.messages) for session in self.sessions.values()),
            "oldest_session": min(
                (session.created_at for session in self.sessions.values()),
                default=None
            )
        }

# Global session manager instance
session_manager = SessionManager()