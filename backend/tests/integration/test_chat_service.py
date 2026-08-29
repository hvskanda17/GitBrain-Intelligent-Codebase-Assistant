import uuid
import pytest

from app.core.exceptions import PermissionDeniedError
from app.db.models.chat import ChatMessage, ChatSession
from app.db.models.repository import Project, Repository
from app.db.models.user import User
from app.repositories.chat_repository import ChatMessageRepository, ChatSessionRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.repository_repository import RepositoryRepository
from app.repositories.user_repository import UserRepository
from app.schemas.chat import ChatSessionCreate, ChatSessionUpdate
from app.services.chat_service import ChatService


@pytest.fixture
async def setup_data(db_session):
    user_repo = UserRepository(db_session)
    project_repo = ProjectRepository(db_session)
    repo_repo = RepositoryRepository(db_session)
    
    user = User(email=f"test_{uuid.uuid4()}@example.com", hashed_password="pwd")
    user = await user_repo.add(user)
    
    project = Project(name="Test Project", owner_id=user.id)
    project = await project_repo.add(project)
    
    repo = Repository(project_id=project.id, remote_url="https://github.com/test/test", default_branch="main")
    repo = await repo_repo.add(repo)
    
    await db_session.commit()
    
    return user, repo


@pytest.fixture
def chat_service(db_session):
    return ChatService(
        chat_session_repo=ChatSessionRepository(db_session),
        chat_message_repo=ChatMessageRepository(db_session),
        repo_repo=RepositoryRepository(db_session),
        project_repo=ProjectRepository(db_session),
    )


@pytest.mark.asyncio(loop_scope="session")
async def test_chat_session_crud(chat_service, setup_data, db_session):
    user, repo = setup_data
    
    # 1. Create Session
    create_data = ChatSessionCreate(repository_id=repo.id)
    session = await chat_service.create_session(user.id, create_data)
    assert session.repository_id == repo.id
    assert session.user_id == user.id
    assert session.is_pinned is False
    assert session.title is None
    await db_session.commit()
    
    # 2. Get Session
    fetched_session = await chat_service.get_session(session.id, user.id)
    assert fetched_session.id == session.id
    
    # 3. List Sessions
    sessions = await chat_service.list_sessions(repo.id, user.id)
    assert len(sessions) == 1
    assert sessions[0].id == session.id
    
    # 4. Rename and Pin Session
    update_data = ChatSessionUpdate(title="My new chat", is_pinned=True)
    updated_session = await chat_service.rename_session(session.id, user.id, update_data)
    assert updated_session.title == "My new chat"
    assert updated_session.is_pinned is True
    await db_session.commit()
    
    # 5. Add Message
    msg = await chat_service.add_message(
        session.id, user.id, role="user", content="Hello", sources=[{"doc": "test"}]
    )
    assert msg.role == "user"
    assert msg.content == "Hello"
    assert msg.sources == [{"doc": "test"}]
    await db_session.commit()
    
    # 6. List Messages
    messages = await chat_service.list_messages(session.id, user.id)
    assert len(messages) == 1
    assert messages[0].id == msg.id
    
    # 7. Delete Session
    await chat_service.delete_session(session.id, user.id)
    await db_session.commit()
    
    # verify deletion
    sessions_after = await chat_service.list_sessions(repo.id, user.id)
    assert len(sessions_after) == 0


@pytest.mark.asyncio(loop_scope="session")
async def test_chat_session_access_control(chat_service, setup_data, db_session):
    user, repo = setup_data
    
    # create another user
    user_repo = UserRepository(db_session)
    other_user = User(email=f"other_{uuid.uuid4()}@example.com", hashed_password="pwd")
    other_user = await user_repo.add(other_user)
    await db_session.commit()
    
    create_data = ChatSessionCreate(repository_id=repo.id)
    
    # other user shouldn't be able to create a session in user's repo
    with pytest.raises(PermissionDeniedError):
        await chat_service.create_session(other_user.id, create_data)
