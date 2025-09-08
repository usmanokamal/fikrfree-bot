# FikrFree Assistant API - Client Integration Examples

## How Developers Will Use Your API

Your API follows REST principles, so developers can integrate it into any application that can make HTTP requests. Here are real-world examples:

---

## 🐍 **Python Integration**

### Simple Python Client
```python
import requests
import json

class FikrFreeAPI:
    def __init__(self, base_url="http://localhost:8000/api/v1"):
        self.base_url = base_url
        self.session_id = None
    
    def start_session(self):
        """Start a new conversation session"""
        response = requests.post(f"{self.base_url}/sessions/start")
        if response.status_code == 200:
            self.session_id = response.json()["session_id"]
            return self.session_id
        raise Exception(f"Failed to create session: {response.text}")
    
    def chat(self, message):
        """Send a message and get response"""
        if not self.session_id:
            self.start_session()
        
        data = {"message": message, "stream": False}
        response = requests.post(
            f"{self.base_url}/sessions/{self.session_id}/chat",
            json=data
        )
        
        if response.status_code == 200:
            return response.json()
        raise Exception(f"Chat failed: {response.text}")
    
    def get_history(self):
        """Get conversation history"""
        response = requests.get(f"{self.base_url}/sessions/{self.session_id}/history")
        return response.json()
    
    def close_session(self):
        """End the session"""
        if self.session_id:
            requests.delete(f"{self.base_url}/sessions/{self.session_id}")
            self.session_id = None

# Usage Example
if __name__ == "__main__":
    # Create API client
    api = FikrFreeAPI("https://your-api-domain.com/api/v1")
    
    try:
        # Start conversation
        session_id = api.start_session()
        print(f"Started session: {session_id}")
        
        # Ask questions
        questions = [
            "What insurance plans do you offer?",
            "Tell me about BIMA Bronze plan",
            "BIMA ke plans ke bare mein batao"  # Roman Urdu
        ]
        
        for question in questions:
            print(f"\n🤔 User: {question}")
            response = api.chat(question)
            print(f"🤖 Bot: {response['response']}")
            print(f"   Language: {response['language_detected']}")
        
        # Get full history
        history = api.get_history()
        print(f"\n📚 Total messages: {history['message_count']}")
        
    finally:
        # Clean up
        api.close_session()
```

### Django Integration
```python
# views.py
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import requests

FIKRFREE_API_URL = "https://your-api-domain.com/api/v1"

@csrf_exempt
def chat_with_fikrfree(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        user_message = data.get('message')
        session_id = request.session.get('fikrfree_session_id')
        
        # Create session if doesn't exist
        if not session_id:
            session_response = requests.post(f"{FIKRFREE_API_URL}/sessions/start")
            session_id = session_response.json()["session_id"]
            request.session['fikrfree_session_id'] = session_id
        
        # Send message
        chat_response = requests.post(
            f"{FIKRFREE_API_URL}/sessions/{session_id}/chat",
            json={"message": user_message}
        )
        
        return JsonResponse(chat_response.json())
```

### Flask Integration
```python
from flask import Flask, request, jsonify, session
import requests
import uuid

app = Flask(__name__)
app.secret_key = 'your-secret-key'

FIKRFREE_API_URL = "https://your-api-domain.com/api/v1"

@app.route('/api/chat', methods=['POST'])
def chat():
    user_message = request.json.get('message')
    
    # Get or create session
    session_id = session.get('fikrfree_session_id')
    if not session_id:
        response = requests.post(f"{FIKRFREE_API_URL}/sessions/start")
        session_id = response.json()["session_id"]
        session['fikrfree_session_id'] = session_id
    
    # Chat with FikrFree
    response = requests.post(
        f"{FIKRFREE_API_URL}/sessions/{session_id}/chat",
        json={"message": user_message}
    )
    
    return jsonify(response.json())

if __name__ == '__main__':
    app.run(debug=True)
```

---

## 🌐 **JavaScript/Node.js Integration**

### Frontend JavaScript (Browser)
```javascript
class FikrFreeAPI {
    constructor(baseUrl = "https://your-api-domain.com/api/v1") {
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
    
    async chat(message, streaming = false) {
        if (!this.sessionId) {
            await this.createSession();
        }
        
        const response = await fetch(`${this.baseUrl}/sessions/${this.sessionId}/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message: message,
                stream: streaming
            })
        });
        
        if (streaming) {
            return this.handleStreamingResponse(response);
        } else {
            return await response.json();
        }
    }
    
    async handleStreamingResponse(response) {
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let fullResponse = '';
        
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            
            const chunk = decoder.decode(value);
            const lines = chunk.split('\n');
            
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const data = JSON.parse(line.slice(6));
                    if (data.type === 'content') {
                        fullResponse += data.chunk;
                        // Update UI with chunk
                        this.onChunkReceived(data.chunk);
                    } else if (data.type === 'complete') {
                        return data;
                    }
                }
            }
        }
    }
    
    onChunkReceived(chunk) {
        // Override this method to handle real-time updates
        console.log('Received chunk:', chunk);
    }
    
    async getHistory() {
        const response = await fetch(`${this.baseUrl}/sessions/${this.sessionId}/history`);
        return await response.json();
    }
    
    async deleteSession() {
        if (this.sessionId) {
            await fetch(`${this.baseUrl}/sessions/${this.sessionId}`, {
                method: 'DELETE'
            });
            this.sessionId = null;
        }
    }
}

// Usage Example
const api = new FikrFreeAPI();

// Simple chat
async function sendMessage() {
    const userInput = document.getElementById('user-input').value;
    const response = await api.chat(userInput);
    
    document.getElementById('chat-area').innerHTML += `
        <div class="user-message">${userInput}</div>
        <div class="bot-message">${response.response}</div>
    `;
}

// Streaming chat with real-time updates
class StreamingChatbot extends FikrFreeAPI {
    onChunkReceived(chunk) {
        // Update UI in real-time
        const botMessage = document.getElementById('current-bot-message');
        botMessage.textContent += chunk;
    }
}
```

### React Component
```jsx
import React, { useState, useEffect } from 'react';

const FikrFreeChatbot = () => {
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [sessionId, setSessionId] = useState(null);
    const [loading, setLoading] = useState(false);
    
    const API_BASE = "https://your-api-domain.com/api/v1";
    
    useEffect(() => {
        // Create session on component mount
        createSession();
    }, []);
    
    const createSession = async () => {
        try {
            const response = await fetch(`${API_BASE}/sessions/start`, {
                method: 'POST'
            });
            const data = await response.json();
            setSessionId(data.session_id);
        } catch (error) {
            console.error('Failed to create session:', error);
        }
    };
    
    const sendMessage = async () => {
        if (!input.trim() || !sessionId) return;
        
        const userMessage = input;
        setInput('');
        setLoading(true);
        
        // Add user message to chat
        setMessages(prev => [...prev, {
            type: 'user',
            content: userMessage,
            timestamp: new Date()
        }]);
        
        try {
            const response = await fetch(`${API_BASE}/sessions/${sessionId}/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    message: userMessage,
                    stream: false
                })
            });
            
            const data = await response.json();
            
            // Add bot response to chat
            setMessages(prev => [...prev, {
                type: 'bot',
                content: data.response,
                language: data.language_detected,
                timestamp: new Date()
            }]);
            
        } catch (error) {
            console.error('Failed to send message:', error);
        } finally {
            setLoading(false);
        }
    };
    
    return (
        <div className="fikrfree-chatbot">
            <div className="chat-messages">
                {messages.map((msg, index) => (
                    <div key={index} className={`message ${msg.type}`}>
                        <div className="content">{msg.content}</div>
                        {msg.language && (
                            <div className="language-indicator">
                                Language: {msg.language}
                            </div>
                        )}
                    </div>
                ))}
                {loading && <div className="loading">Bot is typing...</div>}
            </div>
            
            <div className="chat-input">
                <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
                    placeholder="Ask about insurance plans..."
                />
                <button onClick={sendMessage} disabled={loading}>
                    Send
                </button>
            </div>
        </div>
    );
};

export default FikrFreeChatbot;
```

### Node.js Backend Integration
```javascript
const express = require('express');
const axios = require('axios');
const app = express();

app.use(express.json());

const FIKRFREE_API_URL = "https://your-api-domain.com/api/v1";

// Session storage (use Redis in production)
const sessions = new Map();

app.post('/api/chat', async (req, res) => {
    try {
        const { message, userId } = req.body;
        
        // Get or create session for user
        let sessionId = sessions.get(userId);
        if (!sessionId) {
            const sessionResponse = await axios.post(`${FIKRFREE_API_URL}/sessions/start`);
            sessionId = sessionResponse.data.session_id;
            sessions.set(userId, sessionId);
        }
        
        // Send message to FikrFree API
        const chatResponse = await axios.post(
            `${FIKRFREE_API_URL}/sessions/${sessionId}/chat`,
            { message }
        );
        
        res.json(chatResponse.data);
        
    } catch (error) {
        console.error('Chat error:', error);
        res.status(500).json({ error: 'Failed to process chat' });
    }
});

app.listen(3000, () => {
    console.log('Server running on port 3000');
});
```

---

## 📱 **Mobile Integration Examples**

### React Native
```javascript
import React, { useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, ScrollView } from 'react-native';

const FikrFreeChatScreen = () => {
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [sessionId, setSessionId] = useState(null);
    
    const API_BASE = "https://your-api-domain.com/api/v1";
    
    const createSession = async () => {
        try {
            const response = await fetch(`${API_BASE}/sessions/start`, {
                method: 'POST'
            });
            const data = await response.json();
            setSessionId(data.session_id);
        } catch (error) {
            console.error('Session creation failed:', error);
        }
    };
    
    const sendMessage = async () => {
        if (!sessionId) await createSession();
        
        const userMessage = input;
        setInput('');
        
        setMessages(prev => [...prev, { type: 'user', text: userMessage }]);
        
        try {
            const response = await fetch(`${API_BASE}/sessions/${sessionId}/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: userMessage })
            });
            
            const data = await response.json();
            setMessages(prev => [...prev, { 
                type: 'bot', 
                text: data.response,
                language: data.language_detected 
            }]);
            
        } catch (error) {
            console.error('Chat failed:', error);
        }
    };
    
    return (
        <View style={{ flex: 1, padding: 20 }}>
            <ScrollView style={{ flex: 1 }}>
                {messages.map((msg, index) => (
                    <View key={index} style={{
                        alignSelf: msg.type === 'user' ? 'flex-end' : 'flex-start',
                        backgroundColor: msg.type === 'user' ? '#007AFF' : '#E5E5EA',
                        padding: 10,
                        margin: 5,
                        borderRadius: 10,
                        maxWidth: '80%'
                    }}>
                        <Text style={{
                            color: msg.type === 'user' ? 'white' : 'black'
                        }}>
                            {msg.text}
                        </Text>
                        {msg.language && (
                            <Text style={{ fontSize: 12, opacity: 0.7 }}>
                                Language: {msg.language}
                            </Text>
                        )}
                    </View>
                ))}
            </ScrollView>
            
            <View style={{ flexDirection: 'row', alignItems: 'center' }}>
                <TextInput
                    style={{
                        flex: 1,
                        borderWidth: 1,
                        borderColor: '#CCC',
                        borderRadius: 20,
                        paddingHorizontal: 15,
                        paddingVertical: 10,
                        marginRight: 10
                    }}
                    value={input}
                    onChangeText={setInput}
                    placeholder="Ask about insurance..."
                    onSubmitEditing={sendMessage}
                />
                <TouchableOpacity
                    onPress={sendMessage}
                    style={{
                        backgroundColor: '#007AFF',
                        paddingHorizontal: 20,
                        paddingVertical: 10,
                        borderRadius: 20
                    }}
                >
                    <Text style={{ color: 'white' }}>Send</Text>
                </TouchableOpacity>
            </View>
        </View>
    );
};

export default FikrFreeChatScreen;
```

---

## 🔧 **Other Programming Languages**

### PHP Integration
```php
<?php
class FikrFreeAPI {
    private $baseUrl;
    private $sessionId;
    
    public function __construct($baseUrl = "https://your-api-domain.com/api/v1") {
        $this->baseUrl = $baseUrl;
    }
    
    public function createSession() {
        $response = $this->makeRequest('POST', '/sessions/start');
        $this->sessionId = $response['session_id'];
        return $this->sessionId;
    }
    
    public function chat($message) {
        if (!$this->sessionId) {
            $this->createSession();
        }
        
        $data = ['message' => $message, 'stream' => false];
        return $this->makeRequest('POST', "/sessions/{$this->sessionId}/chat", $data);
    }
    
    private function makeRequest($method, $endpoint, $data = null) {
        $url = $this->baseUrl . $endpoint;
        $ch = curl_init();
        
        curl_setopt_array($ch, [
            CURLOPT_URL => $url,
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_CUSTOMREQUEST => $method,
            CURLOPT_HTTPHEADER => ['Content-Type: application/json'],
        ]);
        
        if ($data) {
            curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($data));
        }
        
        $response = curl_exec($ch);
        curl_close($ch);
        
        return json_decode($response, true);
    }
}

// Usage
$api = new FikrFreeAPI();
$response = $api->chat("What are BIMA insurance plans?");
echo $response['response'];
?>
```

### Java Integration
```java
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.net.URI;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.Map;

public class FikrFreeAPI {
    private final String baseUrl;
    private final HttpClient client;
    private final ObjectMapper mapper;
    private String sessionId;
    
    public FikrFreeAPI(String baseUrl) {
        this.baseUrl = baseUrl;
        this.client = HttpClient.newHttpClient();
        this.mapper = new ObjectMapper();
    }
    
    public String createSession() throws Exception {
        HttpRequest request = HttpRequest.newBuilder()
            .uri(URI.create(baseUrl + "/sessions/start"))
            .POST(HttpRequest.BodyPublishers.noBody())
            .build();
            
        HttpResponse<String> response = client.send(request, 
            HttpResponse.BodyHandlers.ofString());
            
        Map<String, Object> data = mapper.readValue(response.body(), Map.class);
        this.sessionId = (String) data.get("session_id");
        return this.sessionId;
    }
    
    public Map<String, Object> chat(String message) throws Exception {
        if (sessionId == null) {
            createSession();
        }
        
        Map<String, Object> requestData = Map.of(
            "message", message,
            "stream", false
        );
        
        HttpRequest request = HttpRequest.newBuilder()
            .uri(URI.create(baseUrl + "/sessions/" + sessionId + "/chat"))
            .POST(HttpRequest.BodyPublishers.ofString(mapper.writeValueAsString(requestData)))
            .header("Content-Type", "application/json")
            .build();
            
        HttpResponse<String> response = client.send(request, 
            HttpResponse.BodyHandlers.ofString());
            
        return mapper.readValue(response.body(), Map.class);
    }
}
```

---

## 🌟 **Real-World Use Cases**

### 1. **Customer Support Chat Widget**
```javascript
// Embed this in any website
<script>
(function() {
    const api = new FikrFreeAPI('https://your-api-domain.com/api/v1');
    
    // Create floating chat widget
    const widget = document.createElement('div');
    widget.innerHTML = `
        <div id="fikrfree-widget" style="position:fixed;bottom:20px;right:20px;z-index:1000;">
            <div id="chat-toggle" style="background:#007AFF;color:white;padding:15px;border-radius:50px;cursor:pointer;">
                💬 Ask about Insurance
            </div>
            <div id="chat-window" style="display:none;background:white;border:1px solid #ccc;width:300px;height:400px;">
                <!-- Chat interface here -->
            </div>
        </div>
    `;
    
    document.body.appendChild(widget);
    
    // Handle chat interactions
    document.getElementById('chat-toggle').onclick = function() {
        const window = document.getElementById('chat-window');
        window.style.display = window.style.display === 'none' ? 'block' : 'none';
    };
})();
</script>
```

### 2. **WhatsApp Bot Integration**
```javascript
// Using WhatsApp Business API
const { Client } = require('whatsapp-web.js');
const FikrFreeAPI = require('./fikrfree-api');

const whatsapp = new Client();
const fikrfree = new FikrFreeAPI();

whatsapp.on('message', async msg => {
    if (msg.body.startsWith('!insurance')) {
        const question = msg.body.replace('!insurance', '').trim();
        const response = await fikrfree.chat(question);
        msg.reply(response.response);
    }
});

whatsapp.initialize();
```

### 3. **Slack Bot Integration**
```javascript
const { App } = require('@slack/bolt');
const FikrFreeAPI = require('./fikrfree-api');

const app = new App({
    token: process.env.SLACK_BOT_TOKEN,
    signingSecret: process.env.SLACK_SIGNING_SECRET
});

const fikrfree = new FikrFreeAPI();

app.message(/insurance|health|bima/i, async ({ message, say }) => {
    const response = await fikrfree.chat(message.text);
    await say(`🏥 ${response.response}`);
});

app.start(3000);
```

---

## 📋 **Quick Integration Checklist**

For developers using your API:

1. **✅ Get API Base URL** (e.g., `https://your-domain.com/api/v1`)
2. **✅ Create Session** (`POST /sessions/start`)
3. **✅ Send Messages** (`POST /sessions/{id}/chat`)
4. **✅ Handle Responses** (JSON with `response`, `language_detected`)
5. **✅ Manage Sessions** (Store session IDs, clean up when done)
6. **✅ Error Handling** (Check HTTP status codes)
7. **✅ Optional: Use Streaming** (Set `stream: true` for real-time responses)

This makes your API incredibly easy to integrate into any application! 🚀