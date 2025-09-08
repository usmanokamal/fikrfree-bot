"""
FikrFree Assistant API Client SDK
A simple Python SDK for integrating with FikrFree Assistant API
"""

import requests
import json
from typing import Optional, Dict, List
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ChatResponse:
    """Response from chat API"""
    session_id: str
    response: str
    language_detected: str
    timestamp: str
    message_count: int


@dataclass
class SessionInfo:
    """Session information"""
    session_id: str
    created_at: str
    last_activity: str
    message_count: int
    is_active: bool


@dataclass
class Message:
    """Chat message"""
    role: str
    content: str
    timestamp: str


class FikrFreeAPIError(Exception):
    """Custom exception for API errors"""
    pass


class FikrFreeClient:
    """
    FikrFree Assistant API Client
    
    A simple, easy-to-use client for the FikrFree Assistant API.
    Handles session management, chat interactions, and error handling.
    
    Example:
        client = FikrFreeClient("https://your-domain.com/api/v1")
        
        # Simple chat
        response = client.chat("What are BIMA insurance plans?")
        print(response.response)
        
        # Multiple messages in same session
        client.chat("Tell me more about Bronze plan")
        client.chat("What about Silver plan?")
        
        # Get conversation history
        history = client.get_history()
    """
    
    def __init__(self, base_url: str = "http://localhost:8000/api/v1"):
        """
        Initialize the FikrFree API client
        
        Args:
            base_url: Base URL of the FikrFree API
        """
        self.base_url = base_url.rstrip('/')
        self.session_id: Optional[str] = None
        self.session = requests.Session()
        
        # Set default headers
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'FikrFree-Python-SDK/1.0'
        })
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
        """Make HTTP request to API"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            if method.upper() == 'GET':
                response = self.session.get(url)
            elif method.upper() == 'POST':
                response = self.session.post(url, json=data)
            elif method.upper() == 'DELETE':
                response = self.session.delete(url)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            # Check for HTTP errors
            if response.status_code >= 400:
                error_msg = f"API request failed with status {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg += f": {error_data.get('message', response.text)}"
                except:
                    error_msg += f": {response.text}"
                raise FikrFreeAPIError(error_msg)
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            raise FikrFreeAPIError(f"Network error: {str(e)}")
    
    def health_check(self) -> Dict:
        """
        Check API health status
        
        Returns:
            Dict with health status information
        """
        return self._make_request('GET', '/health')
    
    def create_session(self) -> str:
        """
        Create a new chat session
        
        Returns:
            Session ID string
        """
        response = self._make_request('POST', '/sessions/start')
        self.session_id = response['session_id']
        return self.session_id
    
    def chat(self, message: str, stream: bool = False, auto_create_session: bool = True) -> ChatResponse:
        """
        Send a message to the chatbot
        
        Args:
            message: Message to send
            stream: Whether to use streaming response (not implemented in this SDK)
            auto_create_session: Automatically create session if none exists
        
        Returns:
            ChatResponse object with bot's reply
        """
        if not message.strip():
            raise ValueError("Message cannot be empty")
        
        # Create session if needed
        if not self.session_id and auto_create_session:
            self.create_session()
        elif not self.session_id:
            raise FikrFreeAPIError("No active session. Call create_session() first or set auto_create_session=True")
        
        # Send message
        data = {"message": message, "stream": stream}
        response = self._make_request('POST', f'/sessions/{self.session_id}/chat', data)
        
        return ChatResponse(
            session_id=response['session_id'],
            response=response['response'],
            language_detected=response['language_detected'],
            timestamp=response['timestamp'],
            message_count=response['message_count']
        )
    
    def get_history(self) -> List[Message]:
        """
        Get conversation history for current session
        
        Returns:
            List of Message objects
        """
        if not self.session_id:
            raise FikrFreeAPIError("No active session")
        
        response = self._make_request('GET', f'/sessions/{self.session_id}/history')
        
        return [
            Message(
                role=msg['role'],
                content=msg['content'],
                timestamp=msg['timestamp']
            )
            for msg in response['messages']
        ]
    
    def get_session_info(self) -> SessionInfo:
        """
        Get information about current session
        
        Returns:
            SessionInfo object
        """
        if not self.session_id:
            raise FikrFreeAPIError("No active session")
        
        response = self._make_request('GET', f'/sessions/{self.session_id}/info')
        
        return SessionInfo(
            session_id=response['session_id'],
            created_at=response['created_at'],
            last_activity=response['last_activity'],
            message_count=response['message_count'],
            is_active=response['is_active']
        )
    
    def delete_session(self) -> bool:
        """
        Delete the current session
        
        Returns:
            True if session was deleted successfully
        """
        if not self.session_id:
            return True  # No session to delete
        
        try:
            self._make_request('DELETE', f'/sessions/{self.session_id}')
            self.session_id = None
            return True
        except FikrFreeAPIError:
            return False
    
    def get_stats(self) -> Dict:
        """
        Get API statistics (requires no session)
        
        Returns:
            Dict with API statistics
        """
        return self._make_request('GET', '/sessions/stats')
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - clean up session"""
        self.delete_session()


# Convenience functions for quick usage
def quick_chat(message: str, api_url: str = "http://localhost:8000/api/v1") -> str:
    """
    Quick one-off chat without session management
    
    Args:
        message: Message to send
        api_url: API base URL
    
    Returns:
        Bot's response as string
    """
    with FikrFreeClient(api_url) as client:
        response = client.chat(message)
        return response.response


def batch_chat(messages: List[str], api_url: str = "http://localhost:8000/api/v1") -> List[ChatResponse]:
    """
    Send multiple messages in a single session
    
    Args:
        messages: List of messages to send
        api_url: API base URL
    
    Returns:
        List of ChatResponse objects
    """
    with FikrFreeClient(api_url) as client:
        responses = []
        for message in messages:
            response = client.chat(message)
            responses.append(response)
        return responses


# Example usage
if __name__ == "__main__":
    # Example 1: Simple usage
    print("=== Example 1: Simple Chat ===")
    response = quick_chat("What are BIMA insurance plans?")
    print(f"Bot: {response}")
    
    print("\n=== Example 2: Session-based Chat ===")
    with FikrFreeClient() as client:
        # Check API health
        health = client.health_check()
        print(f"API Status: {health['status']}")
        
        # Chat with context
        questions = [
            "What insurance plans do you offer?",
            "Tell me more about BIMA Bronze plan",
            "What's the price?",
            "BIMA ke plans ke bare mein batao"  # Roman Urdu
        ]
        
        for question in questions:
            print(f"\nUser: {question}")
            response = client.chat(question)
            print(f"Bot ({response.language_detected}): {response.response[:100]}...")
        
        # Show conversation history
        print(f"\n=== Conversation History ===")
        history = client.get_history()
        print(f"Total messages: {len(history)}")
        
        for i, msg in enumerate(history[-4:], 1):  # Show last 4 messages
            role = "You" if msg.role == "user" else "Bot"
            print(f"{i}. {role}: {msg.content[:50]}...")
    
    print("\n=== Example 3: Batch Processing ===")
    questions = [
        "What is FikrFree?",
        "How do I file a claim?",
        "What are your contact details?"
    ]
    
    responses = batch_chat(questions)
    for i, response in enumerate(responses, 1):
        print(f"{i}. Language: {response.language_detected}")
        print(f"   Response: {response.response[:80]}...")
    
    print("\n=== Example 4: Error Handling ===")
    try:
        # This will fail with invalid URL
        client = FikrFreeClient("http://invalid-url")
        client.chat("Hello")
    except FikrFreeAPIError as e:
        print(f"API Error: {e}")
    
    print("\nSDK demonstration complete! 🎉")