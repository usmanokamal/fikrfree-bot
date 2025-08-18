# FikrFree Assistant API - Developer Package

## 🚀 **Quick Start**

### **API Endpoint**
```
Base URL: https://your-domain.com/api/v1
Interactive Docs: https://your-domain.com/docs
```

### **Test the API (30 seconds)**

**In Browser:** Visit `https://your-domain.com/api/v1` for a welcome message with all endpoints!

**Command Line:**
```bash
# 1. Welcome message
curl https://your-domain.com/api/v1

# 2. Health check
curl https://your-domain.com/api/v1/health

# 3. Create session
SESSION=$(curl -s -X POST https://your-domain.com/api/v1/sessions/start | jq -r .session_id)

# 4. Chat
curl -X POST https://your-domain.com/api/v1/sessions/$SESSION/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What are BIMA insurance plans?"}'
```

---

## 🐍 **Python Integration (Recommended)**

### Quick Setup
```bash
# Download our Python SDK
wget https://your-domain.com/fikrfree_client_sdk.py
```

### Usage
```python
from fikrfree_client_sdk import FikrFreeClient

# Simple chat
with FikrFreeClient("https://your-domain.com/api/v1") as client:
    response = client.chat("What insurance plans do you offer?")
    print(response.response)
    
    # Roman Urdu also works!
    response = client.chat("BIMA ke plans kya hain?")
    print(response.response)  # Responds in Roman Urdu
```

---

## 🌐 **JavaScript Integration**

### Quick Setup
```bash
# Download our JavaScript SDK
wget https://your-domain.com/fikrfree-client-sdk.js
```

### Usage
```javascript
// Browser or Node.js
const client = new FikrFreeClient('https://your-domain.com/api/v1');

const response = await client.chat('Tell me about your services');
console.log(response.response);

// Streaming responses
client.onChunk = (chunk) => console.log(chunk); // Real-time typing
const streamResponse = await client.chat('What is FikrFree?', true);
```

---

## 📱 **Quick Integration Examples**

### React Component
```jsx
import { useState } from 'react';
import { FikrFreeClient } from './fikrfree-client-sdk.js';

function ChatBot() {
    const [response, setResponse] = useState('');
    const client = new FikrFreeClient('https://your-domain.com/api/v1');
    
    const handleChat = async (message) => {
        const result = await client.chat(message);
        setResponse(result.response);
    };
    
    return (
        <div>
            <button onClick={() => handleChat('What are your services?')}>
                Ask about services
            </button>
            <p>{response}</p>
        </div>
    );
}
```

### Django View
```python
from django.http import JsonResponse
from fikrfree_client_sdk import FikrFreeClient

def chat_api(request):
    client = FikrFreeClient("https://your-domain.com/api/v1")
    message = request.POST.get('message')
    response = client.chat(message)
    return JsonResponse({
        'response': response.response,
        'language': response.language_detected
    })
```

### PHP Integration
```php
<?php
// Simple HTTP requests
$session_response = file_get_contents('https://your-domain.com/api/v1/sessions/start', 
    false, stream_context_create(['http' => ['method' => 'POST']]));
$session_id = json_decode($session_response, true)['session_id'];

$chat_data = json_encode(['message' => 'What are your insurance plans?']);
$chat_response = file_get_contents(
    "https://your-domain.com/api/v1/sessions/$session_id/chat",
    false, stream_context_create([
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

## 🎯 **Key Features**

- ✅ **Bilingual**: Responds in English or Roman Urdu automatically
- ✅ **Context-Aware**: Remembers conversation history
- ✅ **Healthcare Expert**: Specialized in Pakistani insurance & healthcare
- ✅ **Real-time**: Streaming responses available
- ✅ **Production Ready**: Error handling, input validation, security
- ✅ **Easy Integration**: Works with any programming language

---

## 📚 **Documentation**

- **Interactive API Docs**: https://your-domain.com/docs
- **Complete Guide**: [API_DOCUMENTATION.md](./API_DOCUMENTATION.md)
- **Code Examples**: [CLIENT_EXAMPLES.md](./CLIENT_EXAMPLES.md)
- **Integration Guide**: [SDK_USAGE_GUIDE.md](./SDK_USAGE_GUIDE.md)

---

## 🆘 **Support**

- **Email**: your-email@domain.com
- **Documentation**: Full guides included in this package
- **Test Environment**: Use the interactive docs to test live

---

## 💡 **Common Use Cases**

1. **Customer Support Bots** - WhatsApp, Telegram, web chat
2. **Mobile Apps** - Healthcare and insurance apps
3. **Website Widgets** - Embedded chat for instant help
4. **Voice Assistants** - Convert responses to speech
5. **Analytics** - Track popular healthcare questions

---

**🚀 Start building in minutes with our ready-to-use SDKs!**