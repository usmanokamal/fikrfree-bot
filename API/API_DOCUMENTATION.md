# FikrFree Assistant API Documentation

## Overview
The FikrFree Assistant API provides programmatic access to the intelligent healthcare chatbot. It supports session-based conversations with context preservation and bilingual communication (English/Roman Urdu).

## Base URL
```
http://localhost:8000/api/v1
```

## Authentication
Currently, no authentication is required. **For production use, implement API keys or OAuth.**

## Key Features
- **Session-based conversations** with context preservation
- **Bilingual support** (English and Roman Urdu)
- **Streaming and non-streaming responses**
- **Automatic language detection**
- **Session management** with automatic cleanup
- **Comprehensive error handling**

---

## API Endpoints

### 1. Health Check
Check if the API is running and get basic statistics.

**Endpoint:** `GET /api/v1/health`

**Response:**
```json
{
  "status": "healthy",
  "service": "FikrFree Assistant API",
  "version": "1.0",
  "timestamp": "2024-01-01T10:00:00Z",
  "active_sessions": 5
}
```

---

### 2. Create Session
Start a new conversation session.

**Endpoint:** `POST /api/v1/sessions/start`

**Response:**
```json
{
  "session_id": "abc123-def456-ghi789",
  "status": "active",
  "created_at": "2024-01-01T10:00:00Z"
}
```

---

### 3. Chat with Session
Send a message to an existing session.

**Endpoint:** `POST /api/v1/sessions/{session_id}/chat`

**Request Body:**
```json
{
  "message": "What are BIMA insurance plans?",
  "stream": false
}
```

**Parameters:**
- `message` (string, required): User message (1-1000 characters)
- `stream` (boolean, optional): Enable streaming response (default: false)

**Non-streaming Response:**
```json
{
  "session_id": "abc123-def456-ghi789",
  "response": "BIMA offers Bronze and Silver insurance plans. Bronze plan costs Rs.1.2 daily and provides Rs.500 hospitalization benefit per night...",
  "language_detected": "english",
  "timestamp": "2024-01-01T10:00:00Z",
  "message_count": 2
}
```

**Streaming Response:**
Server-sent events format with `data:` prefix:
```
data: {"session_id": "abc123", "chunk": "BIMA", "type": "content", "timestamp": "2024-01-01T10:00:00Z"}
data: {"session_id": "abc123", "chunk": " offers", "type": "content", "timestamp": "2024-01-01T10:00:01Z"}
...
data: {"session_id": "abc123", "type": "complete", "full_response": "BIMA offers...", "language_detected": "english", "message_count": 2}
```

---

### 4. Get Session History
Retrieve conversation history for a session.

**Endpoint:** `GET /api/v1/sessions/{session_id}/history`

**Response:**
```json
{
  "session_id": "abc123-def456-ghi789",
  "messages": [
    {
      "role": "user",
      "content": "Hello",
      "timestamp": "2024-01-01T10:00:00Z"
    },
    {
      "role": "assistant",
      "content": "Hello! How can I help you today?",
      "timestamp": "2024-01-01T10:00:01Z"
    }
  ],
  "message_count": 2,
  "created_at": "2024-01-01T10:00:00Z",
  "last_activity": "2024-01-01T10:00:01Z"
}
```

---

### 5. Get Session Info
Get basic information about a session.

**Endpoint:** `GET /api/v1/sessions/{session_id}/info`

**Response:**
```json
{
  "session_id": "abc123-def456-ghi789",
  "created_at": "2024-01-01T10:00:00Z",
  "last_activity": "2024-01-01T10:00:01Z",
  "message_count": 2,
  "is_active": true
}
```

---

### 6. Delete Session
End and delete a conversation session.

**Endpoint:** `DELETE /api/v1/sessions/{session_id}`

**Response:**
```json
{
  "message": "Session abc123-def456-ghi789 deleted successfully",
  "timestamp": "2024-01-01T10:00:00Z"
}
```

---

### 7. Session Statistics
Get statistics about all active sessions.

**Endpoint:** `GET /api/v1/sessions/stats`

**Response:**
```json
{
  "active_sessions": 5,
  "total_messages": 50,
  "oldest_session": "2024-01-01T08:00:00Z",
  "timestamp": "2024-01-01T10:00:00Z"
}
```

---

## Error Responses

All errors follow this format:
```json
{
  "error": "HTTP 404",
  "message": "Session abc123 not found or expired",
  "timestamp": "2024-01-01T10:00:00Z"
}
```

**Common Error Codes:**
- `400`: Bad Request (invalid message, empty content)
- `404`: Session Not Found (session doesn't exist or expired)
- `500`: Internal Server Error (processing failed)

---

## Usage Examples

### Example 1: Simple Conversation

```bash
# 1. Create session
curl -X POST http://localhost:8000/api/v1/sessions/start

# 2. Send message
curl -X POST http://localhost:8000/api/v1/sessions/abc123/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What insurance plans do you have?"}'

# 3. Get history
curl http://localhost:8000/api/v1/sessions/abc123/history

# 4. Delete session
curl -X DELETE http://localhost:8000/api/v1/sessions/abc123
```

### Example 2: Streaming Response

```bash
curl -X POST http://localhost:8000/api/v1/sessions/abc123/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Tell me about BIMA plans", "stream": true}' \
  --no-buffer
```

### Example 3: Roman Urdu Support

```bash
curl -X POST http://localhost:8000/api/v1/sessions/abc123/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "BIMA ke plans kya hain?"}'
```

---

## Python SDK Example

```python
import requests
import json

class FikrFreeAPI:
    def __init__(self, base_url="http://localhost:8000/api/v1"):
        self.base_url = base_url
        self.session_id = None
    
    def create_session(self):
        response = requests.post(f"{self.base_url}/sessions/start")
        self.session_id = response.json()["session_id"]
        return self.session_id
    
    def chat(self, message, stream=False):
        data = {"message": message, "stream": stream}
        response = requests.post(
            f"{self.base_url}/sessions/{self.session_id}/chat",
            json=data
        )
        return response.json()
    
    def get_history(self):
        response = requests.get(f"{self.base_url}/sessions/{self.session_id}/history")
        return response.json()
    
    def delete_session(self):
        response = requests.delete(f"{self.base_url}/sessions/{self.session_id}")
        return response.json()

# Usage
api = FikrFreeAPI()
session_id = api.create_session()
print(f"Created session: {session_id}")

response = api.chat("What are your insurance plans?")
print(f"Response: {response['response']}")

history = api.get_history()
print(f"Message count: {history['message_count']}")

api.delete_session()
```

---

## JavaScript SDK Example

```javascript
class FikrFreeAPI {
    constructor(baseUrl = "http://localhost:8000/api/v1") {
        this.baseUrl = baseUrl;
        this.sessionId = null;
    }
    
    async createSession() {
        const response = await fetch(`${this.baseUrl}/sessions/start`, {
            method: 'POST'
        });
        const data = await response.json();
        this.sessionId = data.session_id;
        return this.sessionId;
    }
    
    async chat(message, stream = false) {
        const response = await fetch(`${this.baseUrl}/sessions/${this.sessionId}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message, stream })
        });
        return await response.json();
    }
    
    async getHistory() {
        const response = await fetch(`${this.baseUrl}/sessions/${this.sessionId}/history`);
        return await response.json();
    }
    
    async deleteSession() {
        const response = await fetch(`${this.baseUrl}/sessions/${this.sessionId}`, {
            method: 'DELETE'
        });
        return await response.json();
    }
}

// Usage
const api = new FikrFreeAPI();
const sessionId = await api.createSession();
console.log(`Created session: ${sessionId}`);

const response = await api.chat("What are your insurance plans?");
console.log(`Response: ${response.response}`);
```

---

## Production Considerations

### Security
1. **Add API authentication** (API keys, OAuth, JWT)
2. **Rate limiting** to prevent abuse
3. **Input validation** and sanitization
4. **CORS restrictions** (remove `*` from allowed origins)
5. **HTTPS only** in production

### Performance
1. **Session cleanup** - expired sessions are automatically removed
2. **Connection pooling** for database connections
3. **Caching** for frequently asked questions
4. **Load balancing** for high traffic

### Monitoring
1. **Logging** all API requests and responses
2. **Metrics** tracking (response time, error rates)
3. **Health checks** and alerting
4. **Session analytics**

### Scalability
1. **External session storage** (Redis, database)
2. **Horizontal scaling** with load balancers
3. **Microservices architecture**
4. **CDN** for static assets

---

## Interactive Documentation

Once your server is running, you can access interactive API documentation at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

These provide live API testing capabilities and complete endpoint documentation.