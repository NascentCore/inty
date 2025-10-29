#!/usr/bin/env python3
"""
Test script for the chatbot demo
"""
import requests
import json
import time

def test_backend():
    """Test the backend API"""
    base_url = "http://localhost:8000"
    
    # Test if backend is running
    try:
        response = requests.get(f"{base_url}/")
        print(f"✅ Backend is running: {response.json()}")
    except requests.exceptions.ConnectionError:
        print("❌ Backend is not running. Please start it first with:")
        print("   cd backend && python main.py")
        return False
    
    # Test chat endpoint
    test_message = {
        "message": "你好，今天天气怎么样？",
        "conversation_history": []
    }
    
    try:
        response = requests.post(
            f"{base_url}/chat",
            json=test_message,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Chat test successful!")
            print(f"   Message: {data['message']}")
            print(f"   Image URL: {data.get('image_url', 'None')}")
            return True
        else:
            print(f"❌ Chat test failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Chat test error: {e}")
        return False

def test_frontend():
    """Test if frontend is accessible"""
    try:
        response = requests.get("http://localhost:3000")
        if response.status_code == 200:
            print("✅ Frontend is running at http://localhost:3000")
            return True
        else:
            print(f"❌ Frontend returned status: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Frontend is not running. Please start it with:")
        print("   cd frontend && npm start")
        return False

if __name__ == "__main__":
    print("🧪 Testing Chatbot Demo...")
    print("=" * 50)
    
    backend_ok = test_backend()
    frontend_ok = test_frontend()
    
    print("=" * 50)
    if backend_ok and frontend_ok:
        print("🎉 All tests passed! Demo is ready to use.")
        print("   Open http://localhost:3000 in your browser")
    else:
        print("⚠️  Some tests failed. Please check the errors above.")