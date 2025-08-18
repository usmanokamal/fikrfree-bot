# FikrFree Assistant API - SDK Usage Guide

## 🚀 **How Others Will Consume Your API**

Your API can be consumed in multiple ways. Here's how developers will integrate it:

---

## 📦 **Option 1: Using Our Python SDK (Easiest)**

### Installation
```bash
# Download the SDK
wget https://your-domain.com/fikrfree_client_sdk.py
# or
curl -O https://your-domain.com/fikrfree_client_sdk.py
```

### Basic Usage
```python
from fikrfree_client_sdk import FikrFreeClient

# Simple chat
client = FikrFreeClient("https://your-api-domain.com/api/v1")
response = client.chat("What are BIMA insurance plans?")
print(response.response)

# Context-aware conversation
client.chat("Tell me about Bronze plan")
client.chat("What's the price?")
client.delete_session()  # Clean up
```

### Advanced Usage
```python
# Context manager (auto cleanup)
with FikrFreeClient("https://your-api-domain.com/api/v1") as client:
    response1 = client.chat("What insurance do you offer?")
    response2 = client.chat("Tell me more about BIMA")
    
    # Get conversation history
    history = client.get_history()
    print(f"Total messages: {len(history)}")

# Quick one-liner
from fikrfree_client_sdk import quick_chat
answer = quick_chat("What is FikrFree?", "https://your-api-domain.com/api/v1")
```

---

## 🌐 **Option 2: Using Our JavaScript SDK**

### Installation
```bash
# Download the SDK
wget https://your-domain.com/fikrfree-client-sdk.js
# or for Node.js projects
npm install node-fetch  # if using Node.js < 18
```

### Browser Usage
```html
<!DOCTYPE html>
<html>
<head>
    <script src="fikrfree-client-sdk.js"></script>
</head>
<body>
    <script>
        const client = new FikrFreeClient('https://your-api-domain.com/api/v1');
        
        async function chat() {
            const response = await client.chat('What are your services?');
            console.log(response.response);
        }
        
        chat();
    </script>
</body>
</html>
```

### Node.js Usage
```javascript
const { FikrFreeClient, quickChat } = require('./fikrfree-client-sdk.js');

// Simple usage
const answer = await quickChat('What insurance plans do you have?');
console.log(answer);

// Advanced usage
const client = new FikrFreeClient('https://your-api-domain.com/api/v1');
await client.chat('Tell me about BIMA');
const history = await client.getHistory();
await client.deleteSession();
```

### React Component
```jsx
import { useState, useEffect } from 'react';
import { FikrFreeClient } from './fikrfree-client-sdk.js';

function ChatBot() {
    const [client] = useState(() => new FikrFreeClient('https://your-api-domain.com/api/v1'));
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    
    const sendMessage = async () => {
        if (!input.trim()) return;
        
        setMessages(prev => [...prev, { type: 'user', content: input }]);
        const response = await client.chat(input);
        setMessages(prev => [...prev, { type: 'bot', content: response.response }]);
        setInput('');
    };
    
    return (
        <div>
            <div className="messages">
                {messages.map((msg, i) => (
                    <div key={i} className={msg.type}>{msg.content}</div>
                ))}
            </div>
            <input 
                value={input} 
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
            />
            <button onClick={sendMessage}>Send</button>
        </div>
    );
}
```

---

## 🔧 **Option 3: Direct HTTP Requests (Any Language)**

### Basic Flow
```javascript
// 1. Create Session
const sessionResponse = await fetch('https://your-api-domain.com/api/v1/sessions/start', {
    method: 'POST'
});
const { session_id } = await sessionResponse.json();

// 2. Send Messages
const chatResponse = await fetch(`https://your-api-domain.com/api/v1/sessions/${session_id}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message: 'What are BIMA plans?' })
});
const { response } = await chatResponse.json();

// 3. Clean Up
await fetch(`https://your-api-domain.com/api/v1/sessions/${session_id}`, { method: 'DELETE' });
```

### Python Requests
```python
import requests

# Create session
session_resp = requests.post('https://your-api-domain.com/api/v1/sessions/start')
session_id = session_resp.json()['session_id']

# Chat
chat_resp = requests.post(
    f'https://your-api-domain.com/api/v1/sessions/{session_id}/chat',
    json={'message': 'What insurance do you offer?'}
)
print(chat_resp.json()['response'])

# Cleanup
requests.delete(f'https://your-api-domain.com/api/v1/sessions/{session_id}')
```

### PHP
```php
<?php
// Create session
$response = file_get_contents('https://your-api-domain.com/api/v1/sessions/start', false, 
    stream_context_create(['http' => ['method' => 'POST']]));
$session_id = json_decode($response, true)['session_id'];

// Chat
$chat_data = json_encode(['message' => 'What are your services?']);
$chat_response = file_get_contents(
    "https://your-api-domain.com/api/v1/sessions/$session_id/chat",
    false,
    stream_context_create([
        'http' => [
            'method' => 'POST',
            'header' => 'Content-Type: application/json',
            'content' => $chat_data
        ]
    ])
);
echo json_decode($chat_response, true)['response'];
?>
```

---

## 🏗️ **Integration Patterns**

### 1. **Chatbot Widget**
```html
<!-- Embed this on any website -->
<div id="fikrfree-widget"></div>
<script>
    const widget = new FikrFreeWidget({
        apiUrl: 'https://your-api-domain.com/api/v1',
        container: '#fikrfree-widget',
        title: 'Ask about Insurance',
        placeholder: 'Type your question...'
    });
</script>
```

### 2. **Customer Support Integration**
```python
# For support tickets
def auto_suggest_response(ticket_message):
    client = FikrFreeClient("https://your-api-domain.com/api/v1")
    suggestion = client.chat(f"How should we respond to: {ticket_message}")
    return suggestion.response
```

### 3. **WhatsApp Bot**
```javascript
const whatsapp = require('whatsapp-web.js');
const { FikrFreeClient } = require('./fikrfree-client-sdk');

const client = new whatsapp.Client();
const fikrfree = new FikrFreeClient('https://your-api-domain.com/api/v1');

client.on('message', async msg => {
    if (msg.body.startsWith('!insurance')) {
        const question = msg.body.replace('!insurance', '').trim();
        const response = await fikrfree.chat(question);
        msg.reply(response.response);
    }
});
```

### 4. **Slack Bot**
```javascript
const { App } = require('@slack/bolt');
const { FikrFreeClient } = require('./fikrfree-client-sdk');

const app = new App({ token: process.env.SLACK_BOT_TOKEN });
const fikrfree = new FikrFreeClient('https://your-api-domain.com/api/v1');

app.message(/insurance|health|bima/i, async ({ message, say }) => {
    const response = await fikrfree.chat(message.text);
    await say(`🏥 ${response.response}`);
});
```

---

## 📊 **What Makes Your API Developer-Friendly**

### ✅ **Easy to Use**
- Simple REST endpoints
- Clear request/response format
- Session-based context
- Automatic language detection

### ✅ **Well Documented**
- Interactive docs at `/docs`
- Code examples in multiple languages
- Ready-to-use SDKs

### ✅ **Production Ready**
- Error handling
- Input validation
- Session management
- Content filtering

### ✅ **Flexible**
- Works with any programming language
- Supports streaming responses
- Bilingual (English/Roman Urdu)
- Context preservation

---

## 🎯 **Common Use Cases**

1. **Website Chat Widget** - Add to any healthcare website
2. **Mobile Apps** - Integrate into insurance mobile apps
3. **Customer Support** - Auto-suggest responses to support agents
4. **WhatsApp/Telegram Bots** - Healthcare information bots
5. **Voice Assistants** - Convert text responses to speech
6. **Analytics Dashboards** - Show popular insurance queries

---

## 📋 **Developer Checklist**

For developers integrating your API:

1. **✅ Get API endpoint** (e.g., `https://your-domain.com/api/v1`)
2. **✅ Choose integration method** (SDK, direct HTTP, or examples)
3. **✅ Test with health check** (`GET /health`)
4. **✅ Implement session management** (create → chat → delete)
5. **✅ Handle errors** (network, API errors)
6. **✅ Add input validation** (non-empty messages)
7. **✅ Optional: Handle streaming** (for real-time responses)

Your API is incredibly developer-friendly and ready for widespread adoption! 🚀