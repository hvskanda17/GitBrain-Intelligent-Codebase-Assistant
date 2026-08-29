import pytest
from httpx import AsyncClient


async def _register_and_login(client: AsyncClient, email: str) -> str:
    await client.post(
        "/api/v1/auth/register", json={"email": email, "password": "correct-horse-battery-staple"}
    )
    resp = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "correct-horse-battery-staple"}
    )
    return resp.json()["access_token"]


@pytest.mark.asyncio(loop_scope="session")
async def test_register_login_and_create_project_and_repository(client: AsyncClient):
    register_resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "senior.eng@example.com",
            "password": "correct-horse-battery-staple",
            "full_name": "Senior Eng",
        },
    )
    assert register_resp.status_code == 201
    assert register_resp.json()["email"] == "senior.eng@example.com"

    # Duplicate registration is rejected
    dup_resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "senior.eng@example.com", "password": "another-password"},
    )
    assert dup_resp.status_code == 409

    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "senior.eng@example.com", "password": "correct-horse-battery-staple"},
    )
    assert login_resp.status_code == 200
    tokens = login_resp.json()
    assert "access_token" in tokens and "refresh_token" in tokens

    # Wrong password is rejected
    bad_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "senior.eng@example.com", "password": "wrong-password"},
    )
    assert bad_login.status_code == 401

    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    # Unauthenticated request is rejected
    unauth_resp = await client.get("/api/v1/projects")
    assert unauth_resp.status_code == 401

    project_resp = await client.post("/api/v1/projects", json={"name": "GitBrain"}, headers=headers)
    assert project_resp.status_code == 201
    project_id = project_resp.json()["id"]

    repo_resp = await client.post(
        "/api/v1/repositories",
        json={"project_id": project_id, "remote_url": "https://github.com/example/gitbrain.git"},
        headers=headers,
    )
    assert repo_resp.status_code == 202
    repository_id = repo_resp.json()["repository_id"]
    assert repo_resp.json()["status"] == "pending"

    status_resp = await client.get(f"/api/v1/repositories/{repository_id}/status", headers=headers)
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == "pending"

    # Refresh rotates the token; the old refresh token can't be reused
    refresh_resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refresh_resp.status_code == 200
    reuse_resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert reuse_resp.status_code == 401


@pytest.mark.asyncio(loop_scope="session")
async def test_cannot_access_another_users_project(client: AsyncClient):
    token_a = await _register_and_login(client, "owner@example.com")
    token_b = await _register_and_login(client, "intruder@example.com")

    project_resp = await client.post(
        "/api/v1/projects", json={"name": "Private Project"}, headers={"Authorization": f"Bearer {token_a}"}
    )
    project_id = project_resp.json()["id"]

    repo_resp = await client.post(
        "/api/v1/repositories",
        json={"project_id": project_id, "remote_url": "https://github.com/example/private.git"},
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert repo_resp.status_code == 403


@pytest.mark.asyncio(loop_scope="session")
async def test_viewer_cannot_trigger_ingestion(client: AsyncClient, db_session):
    # Registration always creates a `developer` by default (see UserRole default in
    # app/db/models/user.py); promoting to `viewer` here exercises the RBAC gate
    # directly against the DB rather than needing an admin-promotion endpoint, which
    # doesn't exist yet.
    from sqlalchemy import update

    from app.db.models.user import User, UserRole

    token = await _register_and_login(client, "viewer@example.com")

    await db_session.execute(
        update(User).where(User.email == "viewer@example.com").values(role=UserRole.VIEWER)
    )
    await db_session.commit()

    project_resp = await client.post(
        "/api/v1/projects", json={"name": "Viewer's Project"}, headers={"Authorization": f"Bearer {token}"}
    )
    project_id = project_resp.json()["id"]

    repo_resp = await client.post(
        "/api/v1/repositories",
        json={"project_id": project_id, "remote_url": "https://github.com/example/repo.git"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert repo_resp.status_code == 403
