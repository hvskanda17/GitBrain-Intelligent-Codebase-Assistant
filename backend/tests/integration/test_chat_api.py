import pytest
from httpx import AsyncClient

from tests.integration.test_auth_and_repositories_api import _register_and_login

@pytest.mark.asyncio(loop_scope="session")
async def test_chat_session_crud(client: AsyncClient):
    # 1. Register and setup project/repo
    token = await _register_and_login(client, "chat.user@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    project_resp = await client.post("/api/v1/projects", json={"name": "Chat Project"}, headers=headers)
    assert project_resp.status_code == 201
    project_id = project_resp.json()["id"]

    repo_resp = await client.post(
        "/api/v1/repositories",
        json={"project_id": project_id, "remote_url": "https://github.com/example/repo.git"},
        headers=headers,
    )
    assert repo_resp.status_code == 202
    repo_id = repo_resp.json()["repository_id"]

    # 2. Create Chat Session
    create_resp = await client.post(
        "/api/v1/chat/sessions",
        json={"repository_id": repo_id},
        headers=headers,
    )
    assert create_resp.status_code == 201
    session = create_resp.json()
    session_id = session["id"]
    assert session["repository_id"] == repo_id
    assert session["is_pinned"] is False
    assert session["title"] is None

    # 3. List Chat Sessions
    list_resp = await client.get(f"/api/v1/chat/sessions?repository_id={repo_id}", headers=headers)
    assert list_resp.status_code == 200
    sessions = list_resp.json()
    assert len(sessions) == 1
    assert sessions[0]["id"] == session_id

    # 4. Get Chat Session
    get_resp = await client.get(f"/api/v1/chat/sessions/{session_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == session_id

    # 5. Patch Chat Session
    patch_resp = await client.patch(
        f"/api/v1/chat/sessions/{session_id}",
        json={"title": "My New Chat", "is_pinned": True},
        headers=headers,
    )
    assert patch_resp.status_code == 200
    patched = patch_resp.json()
    assert patched["title"] == "My New Chat"
    assert patched["is_pinned"] is True

    # 6. Delete Chat Session
    del_resp = await client.delete(f"/api/v1/chat/sessions/{session_id}", headers=headers)
    assert del_resp.status_code == 204

    # Verify deleted
    get_del = await client.get(f"/api/v1/chat/sessions/{session_id}", headers=headers)
    assert get_del.status_code == 404
