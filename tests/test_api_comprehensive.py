import pytest
import httpx
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.database import get_db, Base
from app.core.config import settings
from main import app

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

@pytest.fixture(scope="module")
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def test_user():
    return {
        "email": "test@example.com",
        "username": "testuser",
        "password": "TestPassword123",
        "first_name": "Test",
        "last_name": "User"
    }

@pytest.fixture
def auth_headers(test_user, setup_database):
    client.post("/api/v1/auth/register", json=test_user)
    response = client.post("/api/v1/auth/login", json={
        "username": test_user["username"],
        "password": test_user["password"]
    })
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

class TestHealthEndpoints:
    def test_root_endpoint(self):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data

    def test_health_check(self):
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["healthy", "unhealthy", "degraded"]
        assert "timestamp" in data
        assert "services" in data

    def test_system_info(self):
        response = client.get("/api/v1/info")
        assert response.status_code == 200
        data = response.json()
        assert "version" in data
        assert "environment" in data
        assert "python_version" in data

class TestAuthentication:
    def test_user_registration(self, setup_database, test_user):
        response = client.post("/api/v1/auth/register", json=test_user)
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == test_user["email"]
        assert data["username"] == test_user["username"]
        assert "id" in data

    def test_user_registration_duplicate_email(self, setup_database, test_user):
        client.post("/api/v1/auth/register", json=test_user)
        
        duplicate_user = test_user.copy()
        duplicate_user["username"] = "differentuser"
        
        response = client.post("/api/v1/auth/register", json=duplicate_user)
        assert response.status_code == 400
        assert "Email already registered" in response.json()["detail"]

    def test_user_login(self, setup_database, test_user):
        client.post("/api/v1/auth/register", json=test_user)
        
        response = client.post("/api/v1/auth/login", json={
            "username": test_user["username"],
            "password": test_user["password"]
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_user_login_invalid_credentials(self, setup_database, test_user):
        client.post("/api/v1/auth/register", json=test_user)
        
        response = client.post("/api/v1/auth/login", json={
            "username": test_user["username"],
            "password": "wrongpassword"
        })
        assert response.status_code == 401
        assert "Invalid credentials" in response.json()["detail"]

    def test_protected_endpoint_without_token(self):
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401

    def test_protected_endpoint_with_token(self, setup_database, test_user, auth_headers):
        response = client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == test_user["username"]
        assert data["email"] == test_user["email"]

    def test_password_validation(self, setup_database):
        invalid_user = {
            "email": "invalid@example.com",
            "username": "invaliduser",
            "password": "weak"
        }
        
        response = client.post("/api/v1/auth/register", json=invalid_user)
        assert response.status_code == 422

class TestBackgroundJobs:
    def test_create_background_job(self, setup_database, test_user, auth_headers):
        job_data = {
            "job_type": "send_email",
            "payload": {
                "to_email": "test@example.com",
                "subject": "Test Email",
                "body": "This is a test email"
            },
            "priority": 1
        }
        
        response = client.post("/api/v1/jobs", json=job_data, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["job_type"] == "send_email"
        assert data["status"] == "pending"
        assert "job_id" in data

    def test_get_background_jobs(self, setup_database, test_user, auth_headers):
        response = client.get("/api/v1/jobs", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "jobs" in data
        assert "total" in data
        assert "page" in data

    def test_send_email_endpoint(self, setup_database, test_user, auth_headers):
        email_data = {
            "to_email": "test@example.com",
            "subject": "Test Email",
            "body": "This is a test email",
            "is_html": False
        }
        
        response = client.post("/api/v1/send-email", json=email_data, headers=auth_headers)
        assert response.status_code == 202
        data = response.json()
        assert "job_id" in data
        assert "message" in data

    def test_send_notification_endpoint(self, setup_database, test_user, auth_headers):
        notification_data = "This is a test notification"
        
        response = client.post("/api/v1/send-notification", json=notification_data, headers=auth_headers)
        assert response.status_code == 202
        data = response.json()
        assert "job_id" in data
        assert "message" in data

class TestUserManagement:
    def test_update_current_user(self, setup_database, test_user, auth_headers):
        update_data = {
            "first_name": "Updated",
            "last_name": "Name"
        }
        
        response = client.put("/api/v1/auth/me", json=update_data, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "Updated"
        assert data["last_name"] == "Name"

    def test_change_password(self, setup_database, test_user, auth_headers):
        password_data = {
            "current_password": test_user["password"],
            "new_password": "NewPassword123"
        }
        
        response = client.post("/api/v1/auth/change-password", json=password_data, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "message" in data

    def test_change_password_invalid_current(self, setup_database, test_user, auth_headers):
        password_data = {
            "current_password": "wrongpassword",
            "new_password": "NewPassword123"
        }
        
        response = client.post("/api/v1/auth/change-password", json=password_data, headers=auth_headers)
        assert response.status_code == 400
        assert "Current password is incorrect" in response.json()["detail"]

class TestErrorHandling:
    def test_404_error(self):
        response = client.get("/api/v1/nonexistent")
        assert response.status_code == 404

    def test_422_validation_error(self):
        response = client.post("/api/v1/auth/register", json={
            "email": "invalid-email",
            "username": "test",
            "password": "weak"
        })
        assert response.status_code == 422

    def test_unauthorized_access(self):
        response = client.get("/api/v1/jobs")
        assert response.status_code == 401
