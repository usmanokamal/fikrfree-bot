/**
 * React Component Example - FikrFree Assistant API
 * Shows how to integrate the API into a React application
 */

import React, { useState, useRef } from 'react';
// Import the SDK (adjust path as needed)
// import { FikrFreeClient } from '../fikrfree-client-sdk.js';

const FikrFreeChatbot = ({ apiUrl = "https://your-domain.com/api/v1" }) => {
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [client] = useState(() => new FikrFreeClient(apiUrl));
    
    const messagesEndRef = useRef(null);
    
    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };
    
    React.useEffect(() => {
        scrollToBottom();
    }, [messages]);
    
    const sendMessage = async () => {
        if (!input.trim() || loading) return;
        
        const userMessage = input.trim();
        setInput('');
        setLoading(true);
        
        // Add user message to chat
        setMessages(prev => [...prev, {
            id: Date.now(),
            type: 'user',
            content: userMessage,
            timestamp: new Date().toLocaleTimeString()
        }]);
        
        try {
            // Send to API
            const response = await client.chat(userMessage);
            
            // Add bot response
            setMessages(prev => [...prev, {
                id: Date.now() + 1,
                type: 'bot',
                content: response.response,
                language: response.language_detected,
                timestamp: new Date().toLocaleTimeString()
            }]);
            
        } catch (error) {
            // Add error message
            setMessages(prev => [...prev, {
                id: Date.now() + 1,
                type: 'error',
                content: `Sorry, something went wrong: ${error.message}`,
                timestamp: new Date().toLocaleTimeString()
            }]);
        } finally {
            setLoading(false);
        }
    };
    
    const handleKeyPress = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    };
    
    const clearChat = async () => {
        setMessages([]);
        await client.deleteSession();
    };
    
    return (
        <div className="fikrfree-chatbot" style={styles.container}>
            <div style={styles.header}>
                <h3>🏥 FikrFree Assistant</h3>
                <button onClick={clearChat} style={styles.clearButton}>
                    Clear Chat
                </button>
            </div>
            
            <div style={styles.messagesContainer}>
                {messages.length === 0 && (
                    <div style={styles.welcomeMessage}>
                        <p>👋 Hello! Ask me about insurance plans, healthcare, or anything related to FikrFree.</p>
                        <p>💬 I can respond in English or Roman Urdu!</p>
                    </div>
                )}
                
                {messages.map((msg) => (
                    <div key={msg.id} style={{
                        ...styles.message,
                        ...(msg.type === 'user' ? styles.userMessage : 
                            msg.type === 'error' ? styles.errorMessage : styles.botMessage)
                    }}>
                        <div style={styles.messageContent}>
                            {msg.content}
                        </div>
                        <div style={styles.messageInfo}>
                            <span>{msg.timestamp}</span>
                            {msg.language && (
                                <span style={styles.languageTag}>
                                    {msg.language}
                                </span>
                            )}
                        </div>
                    </div>
                ))}
                
                {loading && (
                    <div style={{...styles.message, ...styles.botMessage}}>
                        <div style={styles.messageContent}>
                            <span style={styles.typing}>Bot is typing...</span>
                        </div>
                    </div>
                )}
                
                <div ref={messagesEndRef} />
            </div>
            
            <div style={styles.inputContainer}>
                <textarea
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyPress={handleKeyPress}
                    placeholder="Ask about insurance plans, healthcare, claims... (English or Roman Urdu)"
                    style={styles.input}
                    rows={2}
                    disabled={loading}
                />
                <button 
                    onClick={sendMessage} 
                    disabled={loading || !input.trim()}
                    style={{
                        ...styles.sendButton,
                        ...(loading || !input.trim() ? styles.sendButtonDisabled : {})
                    }}
                >
                    {loading ? '⏳' : '📤'}
                </button>
            </div>
        </div>
    );
};

// Styles
const styles = {
    container: {
        width: '400px',
        height: '600px',
        border: '1px solid #ddd',
        borderRadius: '10px',
        display: 'flex',
        flexDirection: 'column',
        backgroundColor: 'white',
        fontFamily: 'Arial, sans-serif'
    },
    header: {
        padding: '15px',
        borderBottom: '1px solid #eee',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        backgroundColor: '#f8f9fa'
    },
    clearButton: {
        padding: '5px 10px',
        border: '1px solid #ddd',
        borderRadius: '5px',
        background: 'white',
        cursor: 'pointer',
        fontSize: '12px'
    },
    messagesContainer: {
        flex: 1,
        padding: '10px',
        overflowY: 'auto',
        display: 'flex',
        flexDirection: 'column',
        gap: '10px'
    },
    welcomeMessage: {
        textAlign: 'center',
        color: '#666',
        padding: '20px',
        fontStyle: 'italic'
    },
    message: {
        maxWidth: '80%',
        padding: '10px',
        borderRadius: '10px',
        wordWrap: 'break-word'
    },
    userMessage: {
        alignSelf: 'flex-end',
        backgroundColor: '#007AFF',
        color: 'white'
    },
    botMessage: {
        alignSelf: 'flex-start',
        backgroundColor: '#E5E5EA',
        color: 'black'
    },
    errorMessage: {
        alignSelf: 'flex-start',
        backgroundColor: '#ffebee',
        color: '#c62828',
        border: '1px solid #ef5350'
    },
    messageContent: {
        marginBottom: '5px'
    },
    messageInfo: {
        display: 'flex',
        justifyContent: 'space-between',
        fontSize: '11px',
        opacity: 0.7
    },
    languageTag: {
        backgroundColor: 'rgba(0,0,0,0.1)',
        padding: '2px 6px',
        borderRadius: '10px',
        fontSize: '10px'
    },
    typing: {
        fontStyle: 'italic',
        opacity: 0.7
    },
    inputContainer: {
        padding: '10px',
        borderTop: '1px solid #eee',
        display: 'flex',
        gap: '10px'
    },
    input: {
        flex: 1,
        padding: '10px',
        border: '1px solid #ddd',
        borderRadius: '5px',
        resize: 'none',
        fontFamily: 'Arial, sans-serif'
    },
    sendButton: {
        padding: '10px 15px',
        border: 'none',
        borderRadius: '5px',
        backgroundColor: '#007AFF',
        color: 'white',
        cursor: 'pointer',
        fontSize: '16px'
    },
    sendButtonDisabled: {
        backgroundColor: '#ccc',
        cursor: 'not-allowed'
    }
};

export default FikrFreeChatbot;