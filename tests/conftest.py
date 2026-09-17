import os

os.environ["DATABASE_URL"] = "sqlite:///./test_app.db"
os.environ["JWT_SECRET_KEY"] = "test-secret"
os.environ["OPENAI_API_KEY"] = "your_key"

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from backend.database import Base, get_db
from backend.main import app

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
Base.metadata.create_all(engine)


def override_get_db():
    from sqlalchemy.orm import Session
    with Session(engine) as session:
        yield session


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)
