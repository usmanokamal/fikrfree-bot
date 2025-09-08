# FikrFree Assistant API - Integration Guide

## Quick Start for Developers

### API Base URL
```
Production: https://your-domain.com/api/v1
Local Testing: http://localhost:8000/api/v1
```

### 1. Basic Usage Flow
```javascript
// 1. Create a session
const sessionResponse = await fetch('BASE_URL/sessions/start', {method: 'POST'});
const {session_id} = await sessionResponse.json();

// 2. Send messages
const chatResponse = await fetch(`BASE_URL/sessions/${session_id}/chat`, {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({message: 'What are your insurance plans?'})
});
const {response} = await chatResponse.json();

console.log(response); // Bot's answer
```

### 2. Python Example
```python
import requests

# Create session
session = requests.post('BASE_URL/sessions/start').json()
session_id = session['session_id']

# Chat
response = requests.post(f'BASE_URL/sessions/{session_id}/chat', 
                        json={'message': 'Tell me about BIMA plans'})
print(response.json()['response'])
```

### 3. Key Features
- **Bilingual**: Supports English and Roman Urdu
- **Context**: Remembers conversation history per session
- **Streaming**: Real-time responses available
- **Healthcare Focus**: Specialized in Pakistani insurance & healthcare

### 4. Authentication
Currently no authentication required. For production use, API keys will be implemented.

### 5. Rate Limits
No current limits. Fair usage expected.

### 6. Support
Contact: your-email@domain.com
Documentation: See API_DOCUMENTATION.md