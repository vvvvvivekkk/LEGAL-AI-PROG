"""Chat conversation endpoints for the Ask page's history sidebar.

    GET    /chats                    list conversations (summaries, newest first)
    POST   /chats                    create an empty conversation
    GET    /chats/{id}               one conversation with its full messages
    POST   /chats/{id}/messages      append one message
    DELETE /chats/{id}               delete a conversation

Storage is a JSON file per conversation (src/chat/store.py), separate from the
LanceDB document index. An appended assistant message carries its whole
verification result, so reopening a conversation shows the original proof.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from src.api.deps import get_chat_store
from src.api.schemas import (
    ChatMessage,
    Conversation,
    ConversationList,
    CreateConversationRequest,
)
from src.chat.store import ChatStore, is_valid_id

router = APIRouter()


def _require_id(conversation_id: str) -> None:
    if not is_valid_id(conversation_id):
        raise HTTPException(status_code=400, detail="Malformed conversation id")


@router.get("/chats", response_model=ConversationList)
def list_chats(store: ChatStore = Depends(get_chat_store)) -> ConversationList:
    return ConversationList(conversations=store.list())


@router.post("/chats", response_model=Conversation)
def create_chat(
    req: CreateConversationRequest | None = None,
    store: ChatStore = Depends(get_chat_store),
) -> Conversation:
    return Conversation(**store.create(title=req.title if req else None))


@router.get("/chats/{conversation_id}", response_model=Conversation)
def get_chat(conversation_id: str, store: ChatStore = Depends(get_chat_store)) -> Conversation:
    _require_id(conversation_id)
    conversation = store.get(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail=f"No conversation {conversation_id}")
    return Conversation(**conversation)


@router.post("/chats/{conversation_id}/messages", response_model=Conversation)
def append_message(
    conversation_id: str,
    message: ChatMessage,
    store: ChatStore = Depends(get_chat_store),
) -> Conversation:
    _require_id(conversation_id)
    if message.role not in ("user", "assistant"):
        raise HTTPException(status_code=422, detail="role must be 'user' or 'assistant'")
    # Drop unset verification fields so a user message doesn't carry a wall of
    # nulls it never had -- but only at the top level. A recursive exclude_none
    # also strips nested nulls such as proof.vcs on an abstained answer, which
    # is a required field, so the stored conversation then fails to re-read.
    payload = {k: v for k, v in message.model_dump().items() if v is not None}
    updated = store.append(conversation_id, payload)
    if updated is None:
        raise HTTPException(status_code=404, detail=f"No conversation {conversation_id}")
    return Conversation(**updated)


@router.delete("/chats/{conversation_id}")
def delete_chat(conversation_id: str, store: ChatStore = Depends(get_chat_store)) -> dict:
    _require_id(conversation_id)
    if not store.delete(conversation_id):
        raise HTTPException(status_code=404, detail=f"No conversation {conversation_id}")
    return {"deleted": conversation_id}
