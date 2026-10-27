import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from backend.main import app
from backend.deps import get_current_user
from backend.database import get_db, Base
from backend.models import User, ChatSession, ChatMessage
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import uuid

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_memory_ai.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_user, None)
    Base.metadata.drop_all(bind=engine)
    import os
    if os.path.exists("./test_memory_ai.db"):
        os.remove("./test_memory_ai.db")

def mock_user_1():
    return User(user_id="USER-111", email="user1@example.com", role="Admin")

def mock_user_2():
    return User(user_id="USER-222", email="user2@example.com", role="Admin")

@patch("langchain.agents.create_agent")
@patch("backend.ai_agent.get_llm")
def test_chat_session_lifecycle(mock_get_llm, mock_create_agent):
    app.dependency_overrides[get_current_user] = mock_user_1
    
    mock_llm = MagicMock()
    mock_get_llm.return_value = mock_llm
    
    mock_agent = MagicMock()
    # Mocking AIMessage returned by agent.invoke
    mock_agent.invoke.return_value = {"messages": [MagicMock(content="Hello from AI")]}
    mock_create_agent.return_value = mock_agent

    # 1. First message creates session
    response = client.post("/api/chat", json={"role": "user", "content": "Hi"})
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "assistant"
    assert data["content"] == "Hello from AI"
    assert "session_id" in data
    
    session_id = data["session_id"]
    
    # Verify DB state
    db = TestingSessionLocal()
    chat_session = db.query(ChatSession).filter_by(session_id=session_id).first()
    assert chat_session is not None
    assert chat_session.user_id == "USER-111"
    
    messages = db.query(ChatMessage).filter_by(session_id=session_id).order_by(ChatMessage.created_at.asc()).all()
    assert len(messages) == 2
    assert messages[0].role == "user"
    assert messages[0].content == "Hi"
    assert messages[1].role == "assistant"
    assert messages[1].content == "Hello from AI"
    db.close()

    # 2. Second message uses the same session
    mock_agent.invoke.return_value = {"messages": [MagicMock(content="Second reply")]}
    
    response2 = client.post("/api/chat", json={"role": "user", "content": "Another question", "session_id": session_id})
    assert response2.status_code == 200
    data2 = response2.json()
    assert data2["session_id"] == session_id
    assert data2["content"] == "Second reply"
    
    # Verify DB state has 4 messages
    db = TestingSessionLocal()
    messages = db.query(ChatMessage).filter_by(session_id=session_id).order_by(ChatMessage.created_at.asc()).all()
    assert len(messages) == 4
    assert messages[2].content == "Another question"
    assert messages[3].content == "Second reply"
    db.close()
    
    # 3. Test unauthorized access (User 2 tries to access User 1's session)
    app.dependency_overrides[get_current_user] = mock_user_2
    response3 = client.post("/api/chat", json={"role": "user", "content": "Sneaky", "session_id": session_id})
    assert response3.status_code == 403
    
    # 4. Test invalid session
    response4 = client.post("/api/chat", json={"role": "user", "content": "Invalid", "session_id": "INVALID-123"})
    assert response4.status_code == 404
