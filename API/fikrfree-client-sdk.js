/**
 * FikrFree Assistant API Client SDK (JavaScript)
 * A simple JavaScript SDK for integrating with FikrFree Assistant API
 * 
 * Usage:
 *   // Node.js
 *   const FikrFreeClient = require('./fikrfree-client-sdk');
 *   
 *   // Browser (ES6 modules)
 *   import FikrFreeClient from './fikrfree-client-sdk.js';
 *   
 *   // Basic usage
 *   const client = new FikrFreeClient('https://your-domain.com/api/v1');
 *   const response = await client.chat('What are BIMA insurance plans?');
 *   console.log(response.response);
 */

class FikrFreeAPIError extends Error {
    constructor(message, statusCode = null) {
        super(message);
        this.name = 'FikrFreeAPIError';
        this.statusCode = statusCode;
    }
}

class FikrFreeClient {
    /**
     * Initialize the FikrFree API client
     * @param {string} baseUrl - Base URL of the FikrFree API
     */
    constructor(baseUrl = 'http://localhost:8000/api/v1') {
        this.baseUrl = baseUrl.replace(/\/$/, '');
        this.sessionId = null;
        this.defaultHeaders = {
            'Content-Type': 'application/json',
            'User-Agent': 'FikrFree-JavaScript-SDK/1.0'
        };
    }

    /**
     * Make HTTP request to API
     * @private
     */
    async _makeRequest(method, endpoint, data = null) {
        const url = `${this.baseUrl}${endpoint}`;
        const options = {
            method: method.toUpperCase(),
            headers: { ...this.defaultHeaders }
        };

        if (data) {
            options.body = JSON.stringify(data);
        }

        try {
            const response = await fetch(url, options);
            
            if (!response.ok) {
                let errorMessage = `API request failed with status ${response.status}`;
                try {
                    const errorData = await response.json();
                    errorMessage += `: ${errorData.message || response.statusText}`;
                } catch {
                    errorMessage += `: ${response.statusText}`;
                }
                throw new FikrFreeAPIError(errorMessage, response.status);
            }

            return await response.json();
        } catch (error) {
            if (error instanceof FikrFreeAPIError) {
                throw error;
            }
            throw new FikrFreeAPIError(`Network error: ${error.message}`);
        }
    }

    /**
     * Check API health status
     * @returns {Promise<Object>} Health status information
     */
    async healthCheck() {
        return await this._makeRequest('GET', '/health');
    }

    /**
     * Create a new chat session
     * @returns {Promise<string>} Session ID
     */
    async createSession() {
        const response = await this._makeRequest('POST', '/sessions/start');
        this.sessionId = response.session_id;
        return this.sessionId;
    }

    /**
     * Send a message to the chatbot
     * @param {string} message - Message to send
     * @param {boolean} stream - Whether to use streaming response
     * @param {boolean} autoCreateSession - Automatically create session if none exists
     * @returns {Promise<Object>} Chat response
     */
    async chat(message, stream = false, autoCreateSession = true) {
        if (!message || !message.trim()) {
            throw new Error('Message cannot be empty');
        }

        // Create session if needed
        if (!this.sessionId && autoCreateSession) {
            await this.createSession();
        } else if (!this.sessionId) {
            throw new FikrFreeAPIError('No active session. Call createSession() first or set autoCreateSession=true');
        }

        const data = { message: message.trim(), stream };

        if (stream) {
            return await this._handleStreamingResponse(data);
        } else {
            return await this._makeRequest('POST', `/sessions/${this.sessionId}/chat`, data);
        }
    }

    /**
     * Handle streaming response
     * @private
     */
    async _handleStreamingResponse(data) {
        const url = `${this.baseUrl}/sessions/${this.sessionId}/chat`;
        const response = await fetch(url, {
            method: 'POST',
            headers: { ...this.defaultHeaders },
            body: JSON.stringify(data)
        });

        if (!response.ok) {
            throw new FikrFreeAPIError(`Streaming request failed: ${response.statusText}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let fullResponse = '';
        let finalData = null;

        const chunks = [];

        try {
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value);
                const lines = chunk.split('\n');

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const eventData = JSON.parse(line.slice(6));
                            
                            if (eventData.type === 'content') {
                                fullResponse += eventData.chunk;
                                chunks.push(eventData.chunk);
                                
                                // Emit chunk event if callback is provided
                                if (this.onChunk) {
                                    this.onChunk(eventData.chunk);
                                }
                            } else if (eventData.type === 'complete') {
                                finalData = eventData;
                                break;
                            } else if (eventData.type === 'error') {
                                throw new FikrFreeAPIError(`Streaming error: ${eventData.message}`);
                            }
                        } catch (parseError) {
                            // Skip invalid JSON lines
                            continue;
                        }
                    }
                }

                if (finalData) break;
            }
        } finally {
            reader.releaseLock();
        }

        return {
            ...finalData,
            chunks,
            full_response: fullResponse
        };
    }

    /**
     * Set callback for streaming chunks
     * @param {function} callback - Function to call for each chunk
     */
    onChunk(callback) {
        this.onChunk = callback;
    }

    /**
     * Get conversation history for current session
     * @returns {Promise<Array>} Array of message objects
     */
    async getHistory() {
        if (!this.sessionId) {
            throw new FikrFreeAPIError('No active session');
        }

        const response = await this._makeRequest('GET', `/sessions/${this.sessionId}/history`);
        return response.messages;
    }

    /**
     * Get information about current session
     * @returns {Promise<Object>} Session information
     */
    async getSessionInfo() {
        if (!this.sessionId) {
            throw new FikrFreeAPIError('No active session');
        }

        return await this._makeRequest('GET', `/sessions/${this.sessionId}/info`);
    }

    /**
     * Delete the current session
     * @returns {Promise<boolean>} True if session was deleted successfully
     */
    async deleteSession() {
        if (!this.sessionId) {
            return true; // No session to delete
        }

        try {
            await this._makeRequest('DELETE', `/sessions/${this.sessionId}`);
            this.sessionId = null;
            return true;
        } catch (error) {
            return false;
        }
    }

    /**
     * Get API statistics
     * @returns {Promise<Object>} API statistics
     */
    async getStats() {
        return await this._makeRequest('GET', '/sessions/stats');
    }
}

// Convenience functions for quick usage

/**
 * Quick one-off chat without session management
 * @param {string} message - Message to send
 * @param {string} apiUrl - API base URL
 * @returns {Promise<string>} Bot's response as string
 */
async function quickChat(message, apiUrl = 'http://localhost:8000/api/v1') {
    const client = new FikrFreeClient(apiUrl);
    try {
        const response = await client.chat(message);
        return response.response;
    } finally {
        await client.deleteSession();
    }
}

/**
 * Send multiple messages in a single session
 * @param {Array<string>} messages - Array of messages to send
 * @param {string} apiUrl - API base URL
 * @returns {Promise<Array>} Array of chat responses
 */
async function batchChat(messages, apiUrl = 'http://localhost:8000/api/v1') {
    const client = new FikrFreeClient(apiUrl);
    const responses = [];
    
    try {
        for (const message of messages) {
            const response = await client.chat(message);
            responses.push(response);
        }
        return responses;
    } finally {
        await client.deleteSession();
    }
}

// Example usage and testing
async function demonstrateSDK() {
    console.log('=== FikrFree JavaScript SDK Demonstration ===\n');

    try {
        // Example 1: Simple usage
        console.log('=== Example 1: Simple Chat ===');
        const response = await quickChat('What are BIMA insurance plans?');
        console.log(`Bot: ${response.substring(0, 100)}...`);

        console.log('\n=== Example 2: Session-based Chat ===');
        const client = new FikrFreeClient();
        
        // Check API health
        const health = await client.healthCheck();
        console.log(`API Status: ${health.status}`);

        // Chat with context
        const questions = [
            'What insurance plans do you offer?',
            'Tell me more about BIMA Bronze plan',
            'What\'s the price?',
            'BIMA ke plans ke bare mein batao' // Roman Urdu
        ];

        for (const question of questions) {
            console.log(`\nUser: ${question}`);
            const response = await client.chat(question);
            console.log(`Bot (${response.language_detected}): ${response.response.substring(0, 80)}...`);
        }

        // Show conversation history
        console.log('\n=== Conversation History ===');
        const history = await client.getHistory();
        console.log(`Total messages: ${history.length}`);

        // Show last 4 messages
        const recentMessages = history.slice(-4);
        recentMessages.forEach((msg, i) => {
            const role = msg.role === 'user' ? 'You' : 'Bot';
            console.log(`${i + 1}. ${role}: ${msg.content.substring(0, 50)}...`);
        });

        // Clean up
        await client.deleteSession();

        console.log('\n=== Example 3: Streaming Chat ===');
        const streamClient = new FikrFreeClient();
        
        // Set up chunk handler
        let streamedText = '';
        streamClient.onChunk = (chunk) => {
            streamedText += chunk;
            process.stdout.write(chunk); // Show real-time typing
        };

        console.log('User: Tell me about your services (streaming)');
        console.log('Bot: ');
        
        const streamResponse = await streamClient.chat('Tell me about your services', true);
        console.log(`\n[Stream complete - Language: ${streamResponse.language_detected}]`);
        
        await streamClient.deleteSession();

        console.log('\n=== Example 4: Batch Processing ===');
        const batchQuestions = [
            'What is FikrFree?',
            'How do I file a claim?',
            'What are your contact details?'
        ];

        const batchResponses = await batchChat(batchQuestions);
        batchResponses.forEach((response, i) => {
            console.log(`${i + 1}. Language: ${response.language_detected}`);
            console.log(`   Response: ${response.response.substring(0, 60)}...`);
        });

    } catch (error) {
        console.error('Error:', error.message);
    }

    console.log('\n=== SDK demonstration complete! 🎉 ===');
}

// Export for different environments
if (typeof module !== 'undefined' && module.exports) {
    // Node.js environment
    module.exports = {
        FikrFreeClient,
        FikrFreeAPIError,
        quickChat,
        batchChat,
        demonstrateSDK
    };
} else if (typeof window !== 'undefined') {
    // Browser environment
    window.FikrFreeClient = FikrFreeClient;
    window.FikrFreeAPIError = FikrFreeAPIError;
    window.quickChat = quickChat;
    window.batchChat = batchChat;
}

// Auto-run demonstration if this file is executed directly
if (typeof require !== 'undefined' && require.main === module) {
    // Check if fetch is available (Node.js 18+ or with polyfill)
    if (typeof fetch === 'undefined') {
        console.log('This example requires Node.js 18+ or a fetch polyfill.');
        console.log('To install fetch polyfill: npm install node-fetch');
        console.log('Then add: global.fetch = require("node-fetch");');
    } else {
        demonstrateSDK().catch(console.error);
    }
}