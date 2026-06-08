import asyncio
import os

import httpx
import pytest_asyncio
from httpx import ASGITransport

TEST_UID = "test-user-1"


async def _make_test_user():
    from db.models import User
    from db.session import AsyncSessionLocal
    async with AsyncSessionLocal() as s:
        u = await s.get(User, TEST_UID)
        if u is None:
            s.add(User(id=TEST_UID, email="demo@x.com", password_hash=""))
            await s.commit()
            u = await s.get(User, TEST_UID)
        return u


@pytest_asyncio.fixture
async def client():
    db_path = "./test_conduit.db"
    from db.session import engine, init_models
    await engine.dispose()
    if os.path.exists(db_path):
        os.remove(db_path)
    await init_models()

    from api.main import app
    from api.deps import get_current_user
    # Bypass Supabase network verification in tests with a fixed user.
    app.dependency_overrides[get_current_user] = _make_test_user

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as c:
        yield c

    app.dependency_overrides.clear()
    if os.path.exists(db_path):
        os.remove(db_path)


async def _wait_status(client, job_id, targets, tries=80):
    status = None
    for _ in range(tries):
        await asyncio.sleep(0.05)
        status = (await client.get(f"/api/jobs/{job_id}")).json()["status"]
        if status in targets:
            return status
    return status


async def test_full_lifecycle(client):
    r = await client.post("/api/jobs", json={"seed_domain": "acme.com"})
    assert r.status_code == 202, r.text
    job_id = r.json()["id"]

    status = await _wait_status(client, job_id, {"AWAITING_APPROVAL", "FAILED", "COMPLETED"})
    assert status == "AWAITING_APPROVAL", status

    review = (await client.get(f"/api/jobs/{job_id}/review")).json()
    assert review["companies"] > 0 and review["deliverable"] > 0
    assert "@" in (review["sample_to"] or "")

    r = await client.post(f"/api/jobs/{job_id}/approve")
    assert r.status_code == 200, r.text

    status = await _wait_status(client, job_id, {"COMPLETED", "FAILED"})
    assert status == "COMPLETED", status

    results = (await client.get(f"/api/jobs/{job_id}/results")).json()
    assert results["stats"]["sent"] > 0
    sent = [r["email"] for r in results["results"] if r["status"] == "SENT"]
    assert len(sent) == len(set(sent))  # no double-send


async def test_cancel_blocks_send(client):
    job_id = (await client.post("/api/jobs", json={"seed_domain": "acme.com"})).json()["id"]
    await _wait_status(client, job_id, {"AWAITING_APPROVAL", "FAILED"})
    r = await client.post(f"/api/jobs/{job_id}/cancel")
    assert r.json()["status"] == "CANCELLED"
    r = await client.post(f"/api/jobs/{job_id}/approve")
    assert r.status_code == 409


async def test_idempotent_submit(client):
    h = {"Idempotency-Key": "abc-123"}
    a = (await client.post("/api/jobs", json={"seed_domain": "acme.com"}, headers=h)).json()
    b = (await client.post("/api/jobs", json={"seed_domain": "acme.com"}, headers=h)).json()
    assert a["id"] == b["id"]


async def test_delete_job(client):
    job_id = (await client.post("/api/jobs", json={"seed_domain": "acme.com"})).json()["id"]
    await _wait_status(client, job_id, {"AWAITING_APPROVAL", "FAILED", "COMPLETED"})
    r = await client.delete(f"/api/jobs/{job_id}")
    assert r.status_code == 204
    assert (await client.get(f"/api/jobs/{job_id}")).status_code == 404
    assert all(j["id"] != job_id for j in (await client.get("/api/jobs")).json())


async def test_auth_required():
    # No dependency override here -> the real Supabase-backed guard runs and,
    # with no bearer token, returns 401 before any network call.
    from api.main import app
    from api.deps import get_current_user
    from db.session import init_models
    await init_models()
    app.dependency_overrides.pop(get_current_user, None)
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as c:
        r = await c.get("/api/jobs")
        assert r.status_code == 401
