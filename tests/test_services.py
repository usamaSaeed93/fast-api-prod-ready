import pytest
from sqlalchemy.orm import Session
from app.core.database import get_db_context
from app.models.user import User, UserSession, AuditLog
from app.models.job import BackgroundJob
from app.services.user_service import UserService, SessionService, AuditService
from app.services.job_service import BackgroundJobService
from app.schemas.auth import UserCreate, UserUpdate
from app.schemas.job import BackgroundJobCreate, JobStatusUpdate, JobStatus, JobPriority
from app.core.auth import PasswordManager, TokenManager
from datetime import datetime, timedelta

@pytest.fixture
def db_session():
    from app.core.database import SessionLocal
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

@pytest.fixture
def sample_user_data():
    return UserCreate(
        email="test@example.com",
        username="testuser",
        password="TestPassword123",
        first_name="Test",
        last_name="User"
    )

class TestUserService:
    def test_create_user(self, db_session, sample_user_data):
        user = UserService.create_user(db_session, sample_user_data)
        
        assert user.email == sample_user_data.email
        assert user.username == sample_user_data.username
        assert user.first_name == sample_user_data.first_name
        assert user.last_name == sample_user_data.last_name
        assert user.is_active is True
        assert user.is_verified is False
        assert user.hashed_password != sample_user_data.password

    def test_get_user_by_email(self, db_session, sample_user_data):
        UserService.create_user(db_session, sample_user_data)
        user = UserService.get_user_by_email(db_session, sample_user_data.email)
        
        assert user is not None
        assert user.email == sample_user_data.email

    def test_get_user_by_username(self, db_session, sample_user_data):
        UserService.create_user(db_session, sample_user_data)
        user = UserService.get_user_by_username(db_session, sample_user_data.username)
        
        assert user is not None
        assert user.username == sample_user_data.username

    def test_update_user(self, db_session, sample_user_data):
        user = UserService.create_user(db_session, sample_user_data)
        
        update_data = UserUpdate(
            first_name="Updated",
            last_name="Name"
        )
        
        updated_user = UserService.update_user(db_session, user.id, update_data)
        
        assert updated_user.first_name == "Updated"
        assert updated_user.last_name == "Name"
        assert updated_user.email == sample_user_data.email

    def test_deactivate_user(self, db_session, sample_user_data):
        user = UserService.create_user(db_session, sample_user_data)
        
        success = UserService.deactivate_user(db_session, user.id)
        assert success is True
        
        updated_user = UserService.get_user_by_id(db_session, user.id)
        assert updated_user.is_active is False

    def test_get_users_with_pagination(self, db_session, sample_user_data):
        for i in range(5):
            user_data = UserCreate(
                email=f"test{i}@example.com",
                username=f"testuser{i}",
                password="TestPassword123"
            )
            UserService.create_user(db_session, user_data)
        
        users, total = UserService.get_users(db_session, skip=0, limit=3)
        
        assert len(users) == 3
        assert total == 5

    def test_get_users_with_search(self, db_session, sample_user_data):
        UserService.create_user(db_session, sample_user_data)
        
        users, total = UserService.get_users(db_session, search="test")
        assert total >= 1
        
        users, total = UserService.get_users(db_session, search="nonexistent")
        assert total == 0

class TestPasswordManager:
    def test_hash_password(self):
        password = "TestPassword123"
        hashed = PasswordManager.hash_password(password)
        
        assert hashed != password
        assert len(hashed) > 0

    def test_verify_password(self):
        password = "TestPassword123"
        hashed = PasswordManager.hash_password(password)
        
        assert PasswordManager.verify_password(password, hashed) is True
        assert PasswordManager.verify_password("wrongpassword", hashed) is False

    def test_validate_password_strength(self):
        assert PasswordManager.validate_password_strength("TestPassword123") is True
        assert PasswordManager.validate_password_strength("weak") is False
        assert PasswordManager.validate_password_strength("nouppercase123") is False
        assert PasswordManager.validate_password_strength("NOLOWERCASE123") is False
        assert PasswordManager.validate_password_strength("NoNumbers") is False

class TestTokenManager:
    def test_create_access_token(self):
        data = {"sub": "testuser"}
        token = TokenManager.create_access_token(data)
        
        assert isinstance(token, str)
        assert len(token) > 0

    def test_verify_token(self):
        data = {"sub": "testuser"}
        token = TokenManager.create_access_token(data)
        
        token_data = TokenManager.verify_token(token)
        
        assert token_data is not None
        assert token_data.username == "testuser"
        assert token_data.token_type == "access"

    def test_verify_invalid_token(self):
        token_data = TokenManager.verify_token("invalid_token")
        assert token_data is None

class TestBackgroundJobService:
    def test_create_job(self, db_session):
        job_data = BackgroundJobCreate(
            job_type="send_email",
            payload={"to": "test@example.com"},
            priority=JobPriority.HIGH
        )
        
        job = BackgroundJobService.create_job(db_session, job_data)
        
        assert job.job_type == "send_email"
        assert job.priority == JobPriority.HIGH.value
        assert job.status == JobStatus.PENDING.value
        assert job.payload is not None

    def test_get_job_by_id(self, db_session):
        job_data = BackgroundJobCreate(job_type="send_email")
        job = BackgroundJobService.create_job(db_session, job_data)
        
        retrieved_job = BackgroundJobService.get_job_by_id(db_session, job.job_id)
        
        assert retrieved_job is not None
        assert retrieved_job.job_id == job.job_id

    def test_update_job_status(self, db_session):
        job_data = BackgroundJobCreate(job_type="send_email")
        job = BackgroundJobService.create_job(db_session, job_data)
        
        status_update = JobStatusUpdate(
            status=JobStatus.COMPLETED,
            result="Job completed successfully"
        )
        
        updated_job = BackgroundJobService.update_job_status(
            db_session, job.job_id, status_update
        )
        
        assert updated_job.status == JobStatus.COMPLETED.value
        assert updated_job.result == "Job completed successfully"
        assert updated_job.completed_at is not None

    def test_get_jobs_with_filters(self, db_session):
        for i in range(3):
            job_data = BackgroundJobCreate(
                job_type="send_email" if i % 2 == 0 else "notification"
            )
            BackgroundJobService.create_job(db_session, job_data)
        
        jobs, total = BackgroundJobService.get_jobs(
            db_session, job_type="send_email"
        )
        
        assert total >= 1
        for job in jobs:
            assert job.job_type == "send_email"

    def test_get_job_statistics(self, db_session):
        for i in range(5):
            job_data = BackgroundJobCreate(job_type="send_email")
            BackgroundJobService.create_job(db_session, job_data)
        
        stats = BackgroundJobService.get_job_statistics(db_session)
        
        assert "total_jobs" in stats
        assert "status_counts" in stats
        assert "type_counts" in stats
        assert stats["total_jobs"] >= 5

class TestAuditService:
    def test_log_action(self, db_session, sample_user_data):
        user = UserService.create_user(db_session, sample_user_data)
        
        audit_log = AuditService.log_action(
            db_session,
            user_id=user.id,
            action="test_action",
            resource_type="test_resource",
            resource_id="123",
            details="Test details"
        )
        
        assert audit_log.user_id == user.id
        assert audit_log.action == "test_action"
        assert audit_log.resource_type == "test_resource"
        assert audit_log.resource_id == "123"
        assert audit_log.details == "Test details"

    def test_get_audit_logs(self, db_session, sample_user_data):
        user = UserService.create_user(db_session, sample_user_data)
        
        for i in range(3):
            AuditService.log_action(
                db_session,
                user_id=user.id,
                action=f"action_{i}",
                resource_type="test_resource"
            )
        
        logs, total = AuditService.get_audit_logs(
            db_session, user_id=user.id
        )
        
        assert total >= 3
        assert len(logs) >= 3
