import asyncio
import os

import httpx
import pytest
import pytest_asyncio
from httpx import ASGITransport


@pytest_asyncio.fixture
async def client():
    # fresh DB file — dispose the pooled engine first so the unlinked inode is
    # fully released and create_all rebuilds an empty schema.
    db_path = "./test_conduit.db"
    from db.session import engine, init_models
    await engine.dispose()
    if os.path.exists(db_path):
        os.remove(db_path)
    await init_models()
    from api.main import app
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as c:
        yield c
    if os.path.exists(db_path):
        os.remove(db_path)


async def _auth(client) -> dict:
    r = await client.post("/api/auth/register",
                          json={"email": "demo@x.com", "password": "password123"})
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _wait_status(client, job_id, headers, targets, tries=80):
    status = None
    for _ in range(tries):
        await asyncio.sleep(0.05)
        status = (await client.get(f"/api/jobs/{job_id}", headers=headers)).json()["status"]
        if status in targets:
            return status
    return status


async def test_full_lifecycle(client):
    H = await _auth(client)

    r = await client.post("/api/jobs", json={"seed_domain": "acme.com"}, headers=H)
    assert r.status_code == 202, r.text
    job_id = r.json()["id"]

    status = await _wait_status(client, job_id, H, {"AWAITING_APPROVAL", "FAILED", "COMPLETED"})
    assert status == "AWAITING_APPROVAL", status

    review = (await client.get(f"/api/jobs/{job_id}/review", headers=H)).json()
    assert review["companies"] > 0 and review["deliverable"] > 0
    assert "@" in (review["sample_to"] or "")

    r = await client.post(f"/api/jobs/{job_id}/approve", headers=H)
    assert r.status_code == 200, r.text

    status = await _wait_status(client, job_id, H, {"COMPLETED", "FAILED"})
    assert status == "COMPLETED", status

    results = (await client.get(f"/api/jobs/{job_id}/results", headers=H)).json()
    assert results["stats"]["sent"] > 0
    sent_emails = [r["email"] for r in results["results"] if r["status"] == "SENT"]
    assert len(sent_emails) == len(set(sent_emails))  # no double-send


async def test_cancel_blocks_send(client):
    H = await _auth(client)
    job_id = (await client.post("/api/jobs", json={"seed_domain": "acme.com"},
                                headers=H)).json()["id"]
    await _wait_status(client, job_id, H, {"AWAITING_APPROVAL", "FAILED"})
    r = await client.post(f"/api/jobs/{job_id}/cancel", headers=H)
    assert r.json()["status"] == "CANCELLED"
    # approving a cancelled job is rejected
    r = await client.post(f"/api/jobs/{job_id}/approve", headers=H)
    assert r.status_code == 409


async def test_idempotent_submit(client):
    H = await _auth(client)
    h2 = {**H, "Idempotency-Key": "abc-123"}
    a = (await client.post("/api/jobs", json={"seed_domain": "acme.com"}, headers=h2)).json()
    b = (await client.post("/api/jobs", json={"seed_domain": "acme.com"}, headers=h2)).json()
    assert a["id"] == b["id"]  # one job, not two


async def test_auth_required(client):
    r = await client.get("/api/jobs")
    assert r.status_code == 401
