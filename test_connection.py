#!/usr/bin/env python3
"""
Quick test script to verify backend connection and frontend setup
"""

import requests
import json
import time

def test_backend_connection():
    """Test if the backend is running and responding."""
    try:
        print("🔍 Testing backend connection...")
        response = requests.get("http://localhost:8000/health", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Backend is running!")
            print(f"   Status: {'Healthy' if data.get('ok') else 'Unhealthy'}")
            print(f"   Blockchain: {'Connected' if data.get('chainConnected') else 'Disconnected'}")
            print(f"   Database: {'Connected' if data.get('dbConnected') else 'Disconnected'}")
            return True
        else:
            print(f"❌ Backend returned status code: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to backend. Is it running on http://localhost:8000?")
        return False
    except Exception as e:
        print(f"❌ Error testing backend: {e}")
        return False

def test_api_endpoints():
    """Test key API endpoints."""
    endpoints = [
        ("/agents", "GET"),
        ("/agent-types", "GET"),
        ("/leaderboard", "GET")
    ]
    
    print("\n🔍 Testing API endpoints...")
    for endpoint, method in endpoints:
        try:
            url = f"http://localhost:8000{endpoint}"
            if method == "GET":
                response = requests.get(url, timeout=5)
            else:
                response = requests.post(url, timeout=5)
            
            if response.status_code == 200:
                print(f"✅ {method} {endpoint} - OK")
            else:
                print(f"⚠️  {method} {endpoint} - Status {response.status_code}")
                
        except Exception as e:
            print(f"❌ {method} {endpoint} - Error: {e}")

def test_frontend_access():
    """Test if frontend is accessible."""
    try:
        print("\n🔍 Testing frontend access...")
        response = requests.get("http://localhost:8080", timeout=5)
        
        if response.status_code == 200:
            print("✅ Frontend is accessible at http://localhost:8080")
            return True
        else:
            print(f"❌ Frontend returned status code: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot access frontend. Is it running on http://localhost:8080?")
        return False
    except Exception as e:
        print(f"❌ Error testing frontend: {e}")
        return False

def main():
    print("🚀 Agent Accountability Platform - Connection Test")
    print("=" * 50)
    
    # Test backend
    backend_ok = test_backend_connection()
    
    if backend_ok:
        test_api_endpoints()
    
    # Test frontend
    frontend_ok = test_frontend_access()
    
    print("\n" + "=" * 50)
    if backend_ok and frontend_ok:
        print("🎉 All systems are running!")
        print("\n📍 Access points:")
        print("   Frontend: http://localhost:8080")
        print("   Backend API: http://localhost:8000")
        print("   API Docs: http://localhost:8000/docs")
        print("\n🧪 Next steps:")
        print("   1. Open http://localhost:8080 in your browser")
        print("   2. Click 'Create Demo Data' to populate with test data")
        print("   3. Test the various features and API endpoints")
    else:
        print("⚠️  Some issues detected:")
        if not backend_ok:
            print("   - Backend is not running or not accessible")
            print("   - Start backend with: cd backend && python main.py")
        if not frontend_ok:
            print("   - Frontend is not running or not accessible")
            print("   - Start frontend with: cd frontend && python -m http.server 8080")

if __name__ == "__main__":
    main()
