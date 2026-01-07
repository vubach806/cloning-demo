"""Pydantic models for Redis schema."""

from typing import Optional, Dict, Any, Literal
from pydantic import BaseModel, Field
from datetime import datetime


class MessageMetadata(BaseModel):
    """Metadata for a conversation message."""

    tokens: int = Field(description="Token count for trimming calculation")
    intent: Optional[str] = Field(None, description="Detected intent of the message")


class ConversationMessage(BaseModel):
    """A single message in the conversation buffer."""

    role: Literal["user", "assistant", "system", "tool"] = Field(description="Sender role")
    content: str = Field(description="Message content")
    timestamp: int = Field(description="Unix timestamp")
    metadata: MessageMetadata = Field(description="Message metadata")


class ActiveContextData(BaseModel):
    """Active context / scratchpad data."""

    current_goal: Optional[str] = Field(None, description="Current goal")
    extracted_entities: Optional[Dict[str, Any]] = Field(None, description="Extracted entities")
    last_tool_used: Optional[str] = Field(None, description="Last tool used")
    total_tokens: int = Field(0, description="Total token count")
    user_mood: Optional[str] = Field(None, description="User mood")
    created_at: Optional[int] = Field(None, description="Creation timestamp")
    updated_at: Optional[int] = Field(None, description="Last update timestamp")
