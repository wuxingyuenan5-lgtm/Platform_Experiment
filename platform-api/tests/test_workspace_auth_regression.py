"""Exercise private workspace writes through the real session/CSRF/API boundary."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.application import create_application
from app.config import get_settings
from app.database import initialize_database
from app.personal_workspace import read_document, save_document
from scripts.user_demo_seed import seed_demo_users


def test_workspace_sessions_isolate_owners_and_reject_csrf_and_stale_writes(monkeypatch):
    settings = get_settings()
    origin = "http://127.0.0.1:4437"
    monkeypatch.setattr(settings, "cors_origins", origin)
    monkeypatch.setattr(settings, "browser_sessions_enabled", True)
    monkeypatch.setattr(settings, "research_refresh_enabled", False)
    initialize_database()
    password = "Isolated workspace regression 2026!"
    users = [
        u for u in seed_demo_users(password=password, prefix="workspace") if u.role == "member"
    ]
    app = create_application()
    url = "/api/v1/me/workspace/events"

    def login(client, user):
        response = client.post(
            "/api/v1/auth/login",
            headers={"Origin": origin},
            json={"username": user.username, "password": password},
        )
        assert response.status_code == 200, response.text
        return {"Origin": origin, "X-CSRF-Token": response.json()["csrfToken"]}

    with TestClient(app) as alice, TestClient(app) as bob:
        alice_headers, bob_headers = login(alice, users[0]), login(bob, users[1])
        event = {"id": "private", "date": "2026-11-03", "title": "Alice research"}
        payload = {"expectedVersion": 0, "events": [event]}
        assert alice.put(url, json=payload).status_code == 403
        assert alice.get(url).json() == {"items": [], "rowVersion": 0}
        saved = alice.put(url, json=payload, headers=alice_headers)
        assert saved.status_code == 200, saved.text
        assert saved.json()["rowVersion"] == 1
        assert bob.get(url).json() == {"items": [], "rowVersion": 0}
        # A token from another valid browser session cannot authorize this write.
        assert bob.put(url, json=payload, headers=alice_headers).status_code == 403
        assert bob.get(url).json()["rowVersion"] == 0
        assert alice.put(url, json=payload, headers=alice_headers).status_code == 409
        assert alice.get(url).json() == saved.json()
        changed = {"expectedVersion": 0, "events": [{**event, "title": "Bob research"}]}
        response = bob.put(url, json=changed, headers=bob_headers)
        assert response.status_code == 200, response.text
        assert bob.get(url).json()["items"][0]["title"] == "Bob research"
        assert alice.get(url).json() == saved.json()


def test_concurrent_workspace_compare_and_swap_has_one_winner():
    initialize_database()
    users = seed_demo_users(password="Isolated workspace concurrency 2026!", prefix="workspacecas")
    user_id = users[0].user_id
    barrier = Barrier(2)

    def save(title):
        barrier.wait(timeout=5)
        try:
            return save_document(user_id, "events", [{"id": title, "title": title}], 0)
        except HTTPException as exc:
            assert exc.status_code == 409
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(save, ["first", "second"]))
    winners = [result for result in results if result is not None]
    assert len(winners) == 1
    assert winners[0]["rowVersion"] == 1
    assert read_document(user_id, "events") == winners[0]
