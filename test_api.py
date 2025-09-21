# API Testing Script
#!/usr/bin/env python3
"""
API Testing Script for FastAPI Authentication & Background Jobs Demo
This script demonstrates the API functionality with real examples.
"""

import requests
import json
import time
from typing import Dict, Any

BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/v1"

class APITester:
    def __init__(self):
        self.session = requests.Session()
        self.token = None
        self.user_data = None
    
    def test_health_check(self):
        """Test the health check endpoint"""
        print("🏥 Testing health check...")
        response = self.session.get(f"{API_BASE}/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health check passed: {data['status']}")
            print(f"   Services: {data['services']}")
        else:
            print(f"❌ Health check failed: {response.status_code}")
        print()
    
    def test_user_registration(self):
        """Test user registration"""
        print("👤 Testing user registration...")
        user_data = {
            "email": "demo@example.com",
            "username": "demouser",
            "password": "demopassword123"
        }
        
        response = self.session.post(f"{API_BASE}/register", json=user_data)
        if response.status_code == 201:
            self.user_data = response.json()
            print(f"✅ User registered successfully: {self.user_data['username']}")
        else:
            print(f"❌ Registration failed: {response.status_code}")
            print(f"   Error: {response.json()}")
        print()
    
    def test_user_login(self):
        """Test user login"""
        print("🔐 Testing user login...")
        login_data = {
            "username": "demouser",
            "password": "demopassword123"
        }
        
        response = self.session.post(f"{API_BASE}/login", json=login_data)
        if response.status_code == 200:
            data = response.json()
            self.token = data["access_token"]
            print(f"✅ Login successful! Token received")
        else:
            print(f"❌ Login failed: {response.status_code}")
            print(f"   Error: {response.json()}")
        print()
    
    def test_protected_endpoints(self):
        """Test protected endpoints"""
        if not self.token:
            print("❌ No token available for protected endpoint tests")
            return
        
        print("🔒 Testing protected endpoints...")
        headers = {"Authorization": f"Bearer {self.token}"}
        
        # Test /me endpoint
        response = self.session.get(f"{API_BASE}/me", headers=headers)
        if response.status_code == 200:
            user_info = response.json()
            print(f"✅ User info retrieved: {user_info['username']}")
        else:
            print(f"❌ Failed to get user info: {response.status_code}")
        
        # Test user update
        update_data = {"username": "updateduser"}
        response = self.session.put(f"{API_BASE}/me", json=update_data, headers=headers)
        if response.status_code == 200:
            updated_user = response.json()
            print(f"✅ User updated: {updated_user['username']}")
        else:
            print(f"❌ Failed to update user: {response.status_code}")
        print()
    
    def test_background_jobs(self):
        """Test background job creation and monitoring"""
        if not self.token:
            print("❌ No token available for background job tests")
            return
        
        print("⚙️  Testing background jobs...")
        headers = {"Authorization": f"Bearer {self.token}"}
        
        # Create a background job
        job_data = {
            "job_type": "send_email",
            "payload": {
                "to_email": "test@example.com",
                "subject": "Test Email from API",
                "body": "This is a test email sent via background job processing!",
                "is_html": False
            }
        }
        
        response = self.session.post(f"{API_BASE}/background-jobs", json=job_data, headers=headers)
        if response.status_code == 201:
            job = response.json()
            job_id = job["job_id"]
            print(f"✅ Background job created: {job_id}")
            
            # Monitor job status
            print("⏳ Monitoring job status...")
            for i in range(5):
                time.sleep(2)
                response = self.session.get(f"{API_BASE}/background-jobs/{job_id}", headers=headers)
                if response.status_code == 200:
                    job_status = response.json()
                    print(f"   Status: {job_status['status']}")
                    if job_status['status'] in ['completed', 'failed']:
                        break
                else:
                    print(f"   Failed to get job status: {response.status_code}")
        else:
            print(f"❌ Failed to create background job: {response.status_code}")
        print()
    
    def test_email_sending(self):
        """Test email sending endpoint"""
        if not self.token:
            print("❌ No token available for email tests")
            return
        
        print("📧 Testing email sending...")
        headers = {"Authorization": f"Bearer {self.token}"}
        
        email_data = {
            "to_email": "demo@example.com",
            "subject": "Test Email from FastAPI Demo",
            "body": "This is a test email sent through the FastAPI demo application!",
            "is_html": False
        }
        
        response = self.session.post(f"{API_BASE}/send-email", json=email_data, headers=headers)
        if response.status_code == 202:
            result = response.json()
            print(f"✅ Email queued for sending: {result['job_id']}")
        else:
            print(f"❌ Failed to queue email: {response.status_code}")
        print()
    
    def test_notification_sending(self):
        """Test notification sending"""
        if not self.token:
            print("❌ No token available for notification tests")
            return
        
        print("🔔 Testing notification sending...")
        headers = {"Authorization": f"Bearer {self.token}"}
        
        notification_data = "Hello! This is a test notification from the FastAPI demo."
        
        response = self.session.post(f"{API_BASE}/send-notification", json=notification_data, headers=headers)
        if response.status_code == 202:
            result = response.json()
            print(f"✅ Notification queued: {result['job_id']}")
        else:
            print(f"❌ Failed to queue notification: {response.status_code}")
        print()
    
    def run_all_tests(self):
        """Run all API tests"""
        print("🧪 Starting API Tests for FastAPI Authentication & Background Jobs Demo")
        print("=" * 70)
        print()
        
        self.test_health_check()
        self.test_user_registration()
        self.test_user_login()
        self.test_protected_endpoints()
        self.test_background_jobs()
        self.test_email_sending()
        self.test_notification_sending()
        
        print("🎉 All tests completed!")
        print()
        print("📚 API Documentation: http://localhost:8000/docs")
        print("🔍 Health Check: http://localhost:8000/api/v1/health")
        print("🐰 RabbitMQ Management: http://localhost:15672 (guest/guest)")


if __name__ == "__main__":
    tester = APITester()
    tester.run_all_tests()
