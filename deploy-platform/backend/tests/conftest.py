import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from sqlalchemy.pool import StaticPool

from app.auth.jwt_handler import create_access_token, hash_password
from app.database import Base, get_db
from app.main import app as fastapi_app

# Ensure all models are imported so Base.metadata knows about them
import app.models.user  # noqa: F401
import app.models.environment  # noqa: F401
import app.models.service  # noqa: F401
import app.models.service_node  # noqa: F401
import app.models.upgrade_package  # noqa: F401
import app.models.upgrade_task  # noqa: F401
import app.models.task_step  # noqa: F401
import app.models.audit_log  # noqa: F401

TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session

    fastapi_app.dependency_overrides[get_db] = override_get_db
    yield TestClient(fastapi_app)
    fastapi_app.dependency_overrides.clear()


@pytest.fixture
def admin_token(db_session):
    from app.models.user import User
    user = User(username="admin", password_hash=hash_password("test-admin-password"), role="admin")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return create_access_token({"sub": str(user.id), "username": user.username, "role": user.role})


@pytest.fixture
def operator_token(db_session):
    from app.models.user import User
    user = User(username="operator", password_hash=hash_password("test-operator-password"), role="operator")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return create_access_token({"sub": str(user.id), "username": user.username, "role": user.role})
