"""Persistent chat conversations for the Ask page.

Deliberately not LanceDB: that index holds document chunks and is rebuilt
whenever the corpus changes, while chat history has to survive that. This is a
plain JSON file per conversation under data/chats/, which is enough for a
single-user local app, is trivially inspectable, and needs no schema migration.

A stored message keeps the *whole* verification result, not just the text --
the VCS, the decision, the answer mode, the context chunk ids and the proof
object -- so reopening an old conversation shows the same proof that was shown
when the answer was first given, rather than a bare transcript.
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_CHATS_DIR = Path("data/chats")

# A title is the first question asked, trimmed to something a sidebar can show.
TITLE_MAX_CHARS = 60

_ID = re.compile(r"^[0-9a-f]{32}$")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id() -> str:
    return uuid.uuid4().hex


def is_valid_id(conversation_id: str) -> bool:
    """Ids are generated hex, so anything else is a bad request -- and this is
    what stops a crafted id from walking out of the chats directory."""
    return bool(_ID.match(conversation_id or ""))


def title_from(text: str) -> str:
    """Sidebar title: the first question, collapsed and truncated."""
    collapsed = " ".join((text or "").split())
    if not collapsed:
        return "New chat"
    if len(collapsed) <= TITLE_MAX_CHARS:
        return collapsed
    return collapsed[: TITLE_MAX_CHARS - 1].rstrip() + "…"


class ChatStore:
    """One JSON file per conversation, under `root`."""

    def __init__(self, root: str | Path = DEFAULT_CHATS_DIR):
        self.root = Path(root)

    def _path(self, conversation_id: str) -> Path:
        if not is_valid_id(conversation_id):
            raise ValueError(f"invalid conversation id: {conversation_id!r}")
        return self.root / f"{conversation_id}.json"

    def _write(self, conversation: dict) -> dict:
        self.root.mkdir(parents=True, exist_ok=True)
        path = self._path(conversation["id"])
        # Write-then-replace, so an interrupted write cannot truncate an
        # existing conversation to half a file.
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(conversation, indent=2), encoding="utf-8")
        tmp.replace(path)
        return conversation

    def create(self, title: str | None = None) -> dict:
        conversation = {
            "id": new_id(),
            "title": title_from(title) if title else "New chat",
            "created_at": _now(),
            "updated_at": _now(),
            "messages": [],
        }
        return self._write(conversation)

    def get(self, conversation_id: str) -> dict | None:
        path = self._path(conversation_id)
        if not path.is_file():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

    def list(self) -> list[dict]:
        """Summaries for the sidebar, newest first. Never returns message bodies."""
        if not self.root.is_dir():
            return []
        summaries = []
        for path in self.root.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue  # a half-written or hand-edited file must not break the list
            summaries.append(
                {
                    "id": data.get("id", path.stem),
                    "title": data.get("title") or "New chat",
                    "created_at": data.get("created_at"),
                    "updated_at": data.get("updated_at"),
                    "message_count": len(data.get("messages", [])),
                }
            )
        summaries.sort(key=lambda s: s.get("updated_at") or "", reverse=True)
        return summaries

    def append(self, conversation_id: str, message: dict) -> dict | None:
        """Add one message. The first user message also titles the conversation."""
        conversation = self.get(conversation_id)
        if conversation is None:
            return None
        message = dict(message)
        message.setdefault("id", new_id())
        message.setdefault("created_at", _now())
        conversation["messages"].append(message)
        conversation["updated_at"] = _now()
        if (
            message.get("role") == "user"
            and conversation.get("title") in (None, "", "New chat")
        ):
            conversation["title"] = title_from(message.get("text", ""))
        return self._write(conversation)

    def delete(self, conversation_id: str) -> bool:
        path = self._path(conversation_id)
        if not path.is_file():
            return False
        path.unlink()
        return True
