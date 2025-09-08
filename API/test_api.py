#!/usr/bin/env python3
"""
test_api.py - Test script for FikrFree Assistant API
Run this after starting the server to test all API endpoints.
"""

import requests
import json
import time
import sys

# Configuration
BASE_URL = "http://localhost:8000/api/v1"
TEST_MESSAGES = [
    "Hello, what can you help me with?",
    "What are BIMA insurance plans?",
    "BIMA ke plans kya hain?",  # Roman Urdu
    "How do I file a claim?",
    "Tell me about doctor consultations"
]

def test_health_check():
    """Test the health check endpoint."""
    print("🏥 Testing health check...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health check passed: {data['status']}")
            print(f"   Active sessions: {data['active_sessions']}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def test_session_creation():
    """Test session creation."""
    print("\n📝 Testing session creation...")
    try:
        response = requests.post(f"{BASE_URL}/sessions/start")
        if response.status_code == 200:
            data = response.json()
            session_id = data["session_id"]
            print(f"✅ Session created: {session_id}")
            return session_id
        else:
            print(f"❌ Session creation failed: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Session creation error: {e}")
        return None

def test_chat(session_id, message, stream=False):
    """Test chat functionality."""
    message_type = "streaming" if stream else "non-streaming"
    print(f"\n💬 Testing {message_type} chat...")
    print(f"   Message: '{message}'")
    
    try:
        payload = {"message": message, "stream": stream}
        response = requests.post(
            f"{BASE_URL}/sessions/{session_id}/chat",
            json=payload
        )
        
        if response.status_code == 200:
            if stream:
                print("✅ Streaming response received:")
                # For simplicity, just show we got a response
                print(f"   Response type: {response.headers.get('content-type')}")
                print("   (Streaming content not fully parsed in this test)")
            else:
                data = response.json()
                print(f"✅ Chat response received:")
                print(f"   Language detected: {data['language_detected']}")
                print(f"   Message count: {data['message_count']}")
                print(f"   Response: {data['response'][:100]}...")
            return True
        else:
            print(f"❌ Chat failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Chat error: {e}")
        return False

def test_session_history(session_id):
    """Test session history retrieval."""
    print(f"\n📚 Testing session history...")
    try:
        response = requests.get(f"{BASE_URL}/sessions/{session_id}/history")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ History retrieved:")
            print(f"   Total messages: {data['message_count']}")
            print(f"   Session created: {data['created_at']}")
            for i, msg in enumerate(data['messages'][-2:], 1):  # Show last 2 messages
                print(f"   Message {i}: [{msg['role']}] {msg['content'][:50]}...")
            return True
        else:
            print(f"❌ History retrieval failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ History retrieval error: {e}")
        return False

def test_session_info(session_id):
    """Test session info retrieval."""
    print(f"\n📊 Testing session info...")
    try:
        response = requests.get(f"{BASE_URL}/sessions/{session_id}/info")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Session info retrieved:")
            print(f"   Session ID: {data['session_id']}")
            print(f"   Message count: {data['message_count']}")
            print(f"   Is active: {data['is_active']}")
            return True
        else:
            print(f"❌ Session info failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Session info error: {e}")
        return False

def test_session_stats():
    """Test session statistics."""
    print(f"\n📈 Testing session stats...")
    try:
        response = requests.get(f"{BASE_URL}/sessions/stats")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Session stats retrieved:")
            print(f"   Active sessions: {data['active_sessions']}")
            print(f"   Total messages: {data['total_messages']}")
            return True
        else:
            print(f"❌ Session stats failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Session stats error: {e}")
        return False

def test_session_deletion(session_id):
    """Test session deletion."""
    print(f"\n🗑️  Testing session deletion...")
    try:
        response = requests.delete(f"{BASE_URL}/sessions/{session_id}")
        if response.status_code == 200:
            print(f"✅ Session deleted successfully")
            return True
        else:
            print(f"❌ Session deletion failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Session deletion error: {e}")
        return False

def test_invalid_session():
    """Test behavior with invalid session ID."""
    print(f"\n🚫 Testing invalid session handling...")
    try:
        response = requests.post(
            f"{BASE_URL}/sessions/invalid-session-id/chat",
            json={"message": "test"}
        )
        if response.status_code == 404:
            print(f"✅ Invalid session properly rejected (404)")
            return True
        else:
            print(f"❌ Invalid session not handled correctly: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Invalid session test error: {e}")
        return False

def main():
    """Run all API tests."""
    print("🚀 Starting FikrFree Assistant API Tests")
    print("=" * 50)
    
    # Track test results
    tests_passed = 0
    tests_total = 0
    
    # Test 1: Health Check
    tests_total += 1
    if test_health_check():
        tests_passed += 1
    
    # Test 2: Session Creation
    tests_total += 1
    session_id = test_session_creation()
    if session_id:
        tests_passed += 1
    else:
        print("❌ Cannot continue without valid session")
        sys.exit(1)
    
    # Test 3: Chat - Multiple messages
    for message in TEST_MESSAGES[:3]:  # Test first 3 messages
        tests_total += 1
        if test_chat(session_id, message):
            tests_passed += 1
        time.sleep(1)  # Brief pause between messages
    
    # Test 4: Streaming Chat
    tests_total += 1
    if test_chat(session_id, "What are your services?", stream=True):
        tests_passed += 1
    
    # Test 5: Session History
    tests_total += 1
    if test_session_history(session_id):
        tests_passed += 1
    
    # Test 6: Session Info
    tests_total += 1
    if test_session_info(session_id):
        tests_passed += 1
    
    # Test 7: Session Stats
    tests_total += 1
    if test_session_stats():
        tests_passed += 1
    
    # Test 8: Invalid Session
    tests_total += 1
    if test_invalid_session():
        tests_passed += 1
    
    # Test 9: Session Deletion
    tests_total += 1
    if test_session_deletion(session_id):
        tests_passed += 1
    
    # Results Summary
    print("\n" + "=" * 50)
    print(f"🏁 Test Results: {tests_passed}/{tests_total} tests passed")
    
    if tests_passed == tests_total:
        print("🎉 All tests passed! Your API is working correctly.")
        print("\n📚 Next steps:")
        print("   1. Check interactive docs: http://localhost:8000/docs")
        print("   2. Read full documentation: API_DOCUMENTATION.md")
        print("   3. Implement authentication for production use")
    else:
        print(f"⚠️  {tests_total - tests_passed} tests failed. Check the logs above.")
        sys.exit(1)

if __name__ == "__main__":
    main()