"""Pydantic models for API request/response."""

from typing import Any
from pydantic import BaseModel


class ToolCallFunction(BaseModel):
    """Function details within a tool call."""
    name: str
    arguments: str  # JSON string


class ToolCall(BaseModel):
    """A tool call from the assistant."""
    id: str
    type: str = "function"
    function: ToolCallFunction


class Message(BaseModel):
    """A chat message."""
    role: str  # "user", "assistant", "tool", "system"
    content: str | None = None
    tool_calls: list[ToolCall] | None = None
    tool_call_id: str | None = None  # For tool responses


class ChatRequest(BaseModel):
    """Request body for /api/chat endpoint."""
    messages: list[Message]


class SSEEvent(BaseModel):
    """Server-Sent Event data."""
    event: str
    data: dict[str, Any]
