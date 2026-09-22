"""Chat history: the full lifecycle a user actually performs.

The headline test walks the real path end to end — create a conversation, ask a
question through /query, store both messages, confirm it is listed, reopen it,
confirm the answer *and its verification result* survive the round trip, then
delete it and confirm it is gone. The point is that reopening an old
conversation shows the original proof, not just the text.
"""

from __future__ import annotations

import pytest

from src.api import deps
from src.api.main import app
from tests.api.conftest import CitingStubAdapter, FakeNLI


@pytest.fixture
def chat_client(client, tmp_path):
    """Base client plus an isolated chat store and stubbed generation/NLI."""
    deps.ApiState.chats_dir = str(tmp_path / "chats")
    app.dependency_overrides[deps.get_adapter_factory] = lambda: (lambda: CitingStubAdapter())
    app.dependency_overrides[deps.get_nli_factory] = lambda: (lambda: FakeNLI())
    yield client
    deps.ApiState.chats_dir = "data/chats"


# ---------------------------------------------------------------------------
# The full lifecycle
# ---------------------------------------------------------------------------

def test_conversation_round_trips_a_real_answer_with_its_verification(
    chat_client, sample_txt_bytes
):
    name, data = sample_txt_bytes
    assert chat_client.post("/ingest", files={"file": (name, data, "text/plain")}).status_code == 200

    # 1. Start a conversation. It exists, empty and untitled.
    created = chat_client.post("/chats", json={}).json()
    conversation_id = created["id"]
    assert created["messages"] == []
    assert created["title"] == "New chat"

    # 2. Ask a real question through the pipeline.
    question = "How long does a landlord have to refund a security deposit?"
    answer = chat_client.post("/query", json={"query": question}).json()
    assert answer["decision"] == "ANSWER"
    assert answer["vcs"] is not None
    assert answer["proof"]["claims"]

    # 3. Store both turns, the assistant one carrying its whole verification.
    chat_client.post(
        f"/chats/{conversation_id}/messages", json={"role": "user", "text": question}
    )
    stored = chat_client.post(
        f"/chats/{conversation_id}/messages",
        json={
            "role": "assistant",
            "text": answer["answer_text"],
            "answer_mode": answer["answer_mode"],
            "decision": answer["decision"],
            "vcs": answer["vcs"],
            "abstained": answer["abstained"],
            "context_chunk_ids": answer["context_chunk_ids"],
            "proof": answer["proof"],
        },
    )
    assert stored.status_code == 200, stored.text

    # 4. It is listed, titled by the first question.
    listing = chat_client.get("/chats").json()["conversations"]
    entry = next(c for c in listing if c["id"] == conversation_id)
    assert entry["title"] == question
    assert entry["message_count"] == 2

    # 5. Reopen it: the text AND the verification come back unchanged.
    reopened = chat_client.get(f"/chats/{conversation_id}").json()
    assert [m["role"] for m in reopened["messages"]] == ["user", "assistant"]

    user_msg, assistant_msg = reopened["messages"]
    assert user_msg["text"] == question

    assert assistant_msg["text"] == answer["answer_text"]
    assert assistant_msg["vcs"] == answer["vcs"]
    assert assistant_msg["decision"] == answer["decision"]
    assert assistant_msg["answer_mode"] == answer["answer_mode"]
    assert assistant_msg["abstained"] == answer["abstained"]
    assert assistant_msg["context_chunk_ids"] == answer["context_chunk_ids"]
    # The proof is what makes this more than a transcript: same claims, same
    # citations, same per-layer verdicts as when the answer was first shown.
    assert assistant_msg["proof"]["claims"] == answer["proof"]["claims"]
    first_claim = assistant_msg["proof"]["claims"][0]
    assert first_claim["supporting_chunk_ids"]
    assert first_claim["verdicts"]["v1_citation"]["passed"] is True

    # 6. Delete it, and it is really gone.
    assert chat_client.delete(f"/chats/{conversation_id}").status_code == 200
    assert chat_client.get(f"/chats/{conversation_id}").status_code == 404
    assert all(c["id"] != conversation_id for c in chat_client.get("/chats").json()["conversations"])


# ---------------------------------------------------------------------------
# Listing, titling, isolation
# ---------------------------------------------------------------------------

def test_new_chat_starts_empty_and_does_not_disturb_existing_ones(chat_client):
    first = chat_client.post("/chats", json={}).json()["id"]
    chat_client.post(f"/chats/{first}/messages", json={"role": "user", "text": "First question"})

    second = chat_client.post("/chats", json={}).json()["id"]
    assert chat_client.get(f"/chats/{second}").json()["messages"] == []
    assert len(chat_client.get(f"/chats/{first}").json()["messages"]) == 1


def test_title_comes_from_the_first_user_message_only(chat_client):
    cid = chat_client.post("/chats", json={}).json()["id"]
    chat_client.post(f"/chats/{cid}/messages", json={"role": "user", "text": "What is the deposit cap?"})
    chat_client.post(f"/chats/{cid}/messages", json={"role": "assistant", "text": "It is 2 months."})
    chat_client.post(f"/chats/{cid}/messages", json={"role": "user", "text": "And the refund window?"})

    assert chat_client.get(f"/chats/{cid}").json()["title"] == "What is the deposit cap?"


def test_long_title_is_truncated_for_the_sidebar(chat_client):
    from src.chat.store import TITLE_MAX_CHARS

    cid = chat_client.post("/chats", json={}).json()["id"]
    chat_client.post(
        f"/chats/{cid}/messages",
        json={"role": "user", "text": "word " * 100},
    )
    title = chat_client.get(f"/chats/{cid}").json()["title"]
    assert len(title) <= TITLE_MAX_CHARS
    assert title.endswith("…")


def test_conversations_are_listed_newest_updated_first(chat_client):
    older = chat_client.post("/chats", json={}).json()["id"]
    newer = chat_client.post("/chats", json={}).json()["id"]
    # Touching the older one makes it the most recently updated.
    chat_client.post(f"/chats/{older}/messages", json={"role": "user", "text": "later"})

    ids = [c["id"] for c in chat_client.get("/chats").json()["conversations"]]
    assert ids.index(older) < ids.index(newer)


def test_listing_is_summaries_not_message_bodies(chat_client):
    cid = chat_client.post("/chats", json={}).json()["id"]
    chat_client.post(f"/chats/{cid}/messages", json={"role": "user", "text": "hello"})

    entry = chat_client.get("/chats").json()["conversations"][0]
    assert entry["message_count"] == 1
    assert "messages" not in entry


def test_no_conversations_lists_empty(chat_client):
    assert chat_client.get("/chats").json()["conversations"] == []


# ---------------------------------------------------------------------------
# Error paths
# ---------------------------------------------------------------------------

def test_unknown_conversation_returns_404(chat_client):
    missing = "0" * 32
    assert chat_client.get(f"/chats/{missing}").status_code == 404
    assert chat_client.delete(f"/chats/{missing}").status_code == 404
    assert chat_client.post(
        f"/chats/{missing}/messages", json={"role": "user", "text": "hi"}
    ).status_code == 404


# An empty id is not in this list: "/chats/" resolves to the listing route, not
# to a lookup with a blank id.
@pytest.mark.parametrize("bad_id", ["../etc/passwd", "not-hex", "  ", "a" * 31, "A" * 32])
def test_malformed_conversation_id_is_rejected(chat_client, bad_id):
    """Ids index a filename, so a crafted one must never reach the filesystem."""
    resp = chat_client.get(f"/chats/{bad_id}")
    assert resp.status_code in (400, 404)


def test_traversal_id_cannot_reach_outside_the_chats_directory(chat_client, tmp_path):
    """The store raises on a non-hex id rather than building a path from it."""
    from src.chat.store import ChatStore

    store = ChatStore(tmp_path / "chats")
    with pytest.raises(ValueError):
        store.get("../../../etc/passwd")
    with pytest.raises(ValueError):
        store.delete("..\..\secrets")


def test_unknown_role_is_rejected(chat_client):
    cid = chat_client.post("/chats", json={}).json()["id"]
    resp = chat_client.post(f"/chats/{cid}/messages", json={"role": "system", "text": "nope"})
    assert resp.status_code == 422


def test_a_corrupt_conversation_file_does_not_break_the_listing(chat_client, tmp_path):
    from pathlib import Path

    good = chat_client.post("/chats", json={}).json()["id"]
    corrupt = Path(deps.ApiState.chats_dir) / f"{'a' * 32}.json"
    corrupt.write_text("{ not json", encoding="utf-8")

    ids = [c["id"] for c in chat_client.get("/chats").json()["conversations"]]
    assert good in ids


# ---------------------------------------------------------------------------
# An abstention round-trips as an abstention
# ---------------------------------------------------------------------------

def test_abstained_answer_round_trips_as_abstained(chat_client):
    cid = chat_client.post("/chats", json={}).json()["id"]
    chat_client.post(
        f"/chats/{cid}/messages",
        json={
            "role": "assistant",
            "text": "INSUFFICIENT_CONTEXT: nothing supports this.",
            "answer_mode": "abstained",
            "decision": "ABSTAIN",
            "vcs": None,
            "abstained": True,
        },
    )
    message = chat_client.get(f"/chats/{cid}").json()["messages"][0]
    assert message["answer_mode"] == "abstained"
    assert message["abstained"] is True
    assert message["vcs"] is None
