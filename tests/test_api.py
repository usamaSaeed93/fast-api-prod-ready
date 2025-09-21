import pytest
import httpx
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import get_db, Base
from app.config import settings
from main import app

# Test database
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
        "password": "testpassword"
    }

def test_root_endpoint():
    """Test the root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    assert "FastAPI Authentication" in response.json()["message"]

def test_health_check():
    """Test the health check endpoint"""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert "services" in data

def test_user_registration(setup_database, test_user):
    """Test user registration"""
    response = client.post("/api/v1/register", json=test_user)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == test_user["email"]
    assert data["username"] == test_user["username"]
    assert "id" in data
    assert "created_at" in data

def test_user_registration_duplicate_email(setup_database, test_user):
    """Test user registration with duplicate email"""
    # Register first user
    client.post("/api/v1/register", json=test_user)
    
    # Try to register with same email
    duplicate_user = test_user.copy()
    duplicate_user["username"] = "differentuser"
    response = client.post("/api/v1/register", json=duplicate_user)
    assert response.status_code == 400
    assert "Email already registered" in response.json()["detail"]

def test_user_login(setup_database, test_user):
    """Test user login"""
    # Register user first
    client.post("/api/v1/register", json=test_user)
    
    # Login
    login_data = {
        "username": test_user["username"],
        "password": test_user["password"]
    }
    response = client.post("/api/v1/login", json=login_data)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_user_login_invalid_credentials(setup_database, test_user):
    """Test user login with invalid credentials"""
    # Register user first
    client.post("/api/v1/register", json=test_user)
    
    # Login with wrong password
    login_data = {
        "username": test_user["username"],
        "password": "wrongpassword"
    }
    response = client.post("/api/v1/login", json=login_data)
    assert response.status_code == 401
    assert "Incorrect username or password" in response.json()["detail"]

def test_protected_endpoint_without_token():
    """Test accessing protected endpoint without token"""
    response = client.get("/api/v1/me")
    assert response.status_code == 401

def test_protected_endpoint_with_token(setup_database, test_user):
    """Test accessing protected endpoint with valid token"""
    # Register and login
    client.post("/api/v1/register", json=test_user)
    login_response = client.post("/api/v1/login", json={
        "username": test_user["username"],
        "password": test_user["password"]
    })
    token = login_response.json()["access_token"]
    
    # Access protected endpoint
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/v1/me", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == test_user["username"]
    assert data["email"] == test_user["email"]

def test_create_background_job(setup_database, test_user):
    """Test creating a background job"""
    # Register and login
    client.post("/api/v1/register", json=test_user)
    login_response = client.post("/api/v1/login", json={
        "username": test_user["username"],
        "password": test_user["password"]
    })
    token = login_response.json()["access_token"]
    
    # Create background job
    headers = {"Authorization": f"Bearer {token}"}
    job_data = {
        "job_type": "send_email",
        "payload": {
            "to_email": "test@example.com",
            "subject": "Test",
            "body": "Test email"
        }
    }
    response = client.post("/api/v1/background-jobs", json=job_data, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["job_type"] == "send_email"
    assert data["status"] == "pending"
    assert "job_id" in data

def test_get_background_jobs(setup_database, test_user):
    """Test getting background jobs"""
    # Register and login
    client.post("/api/v1/register", json=test_user)
    login_response = client.post("/api/v1/login", json={
        "username": test_user["username"],
        "password": test_user["password"]
    })
    token = login_response.json()["access_token"]
    
    # Get background jobs
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/v1/background-jobs", headers=headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)
