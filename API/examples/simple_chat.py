#!/usr/bin/env python3
"""
Simple Chat Example - FikrFree Assistant API
Shows basic usage of the Python SDK
"""

import sys
import os

# Add parent directory to path to import the SDK
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fikrfree_client_sdk import FikrFreeClient

def main():
    # Replace with your actual API URL
    API_URL = "https://your-domain.com/api/v1"
    
    print("🤖 FikrFree Assistant - Simple Chat Example")
    print("=" * 50)
    
    # Create client
    client = FikrFreeClient(API_URL)
    
    try:
        # Test health
        health = client.health_check()
        print(f"✅ API Status: {health['status']}")
        
        # Simple questions
        questions = [
            "What is FikrFree?",
            "What insurance plans do you offer?",
            "Tell me about BIMA Bronze plan",
            "BIMA ke plans kya hain?",  # Roman Urdu
        ]
        
        for question in questions:
            print(f"\n❓ Question: {question}")
            response = client.chat(question)
            print(f"🤖 Response ({response.language_detected}): {response.response[:100]}...")
        
        print(f"\n📊 Total messages in conversation: {len(client.get_history())}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    
    finally:
        # Clean up
        client.delete_session()
        print("\n✅ Session cleaned up")

if __name__ == "__main__":
    main()