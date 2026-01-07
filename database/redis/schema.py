"""Redis schema implementation for short-term memory."""

import json
import time
from typing import List, Optional, Dict, Any
from redis import Redis
from database.connection import db_manager
from database.redis.models import ConversationMessage, ActiveContextData, MessageMetadata


class ConversationBuffer:
    """Manages conversation buffer using Redis linked list.

    Key naming: agent:stm:chat:{session_id}
    Data structure: Linked List
    Methods: RPUSH, LRANGE, LTRIM
    """

    def __init__(self, session_id: str, redis_client: Optional[Redis] = None):
        """Initialize conversation buffer.

        Args:
            session_id: Unique session identifier
            redis_client: Redis client instance (uses db_manager if not provided)
        """
        self.session_id = session_id
        self.redis_client = redis_client or db_manager.connect_redis()
        self.key = f"agent:stm:chat:{session_id}"

    def add_message(
        self,
        role: str,
        content: str,
        tokens: int = 0,
        intent: Optional[str] = None,
        ttl: Optional[int] = None,
    ) -> None:
        """Add a new message to the conversation buffer.

        Args:
            role: Message role (user, assistant, system, tool)
            content: Message content
            tokens: Token count for this message
            intent: Detected intent (optional)
            ttl: Time to live in seconds (resets TTL if provided)
        """
        message = ConversationMessage(
            role=role,
            content=content,
            timestamp=int(time.time()),
            metadata=MessageMetadata(tokens=tokens, intent=intent),
        )

        # Add message to list
        self.redis_client.rpush(self.key, message.model_dump_json())

        # Reset TTL on new interaction
        if ttl:
            self.redis_client.expire(self.key, ttl)

    def get_messages(self, start: int = 0, end: int = -1) -> List[ConversationMessage]:
        """Retrieve conversation messages.

        Args:
            start: Start index (0-based)
            end: End index (-1 for all)

        Returns:
            List of conversation messages
        """
        messages_json = self.redis_client.lrange(self.key, start, end)
        return [ConversationMessage.model_validate_json(msg) for msg in messages_json]

    def trim_conversation(self, max_messages: int) -> None:
        """Trim conversation to keep only the most recent messages.

        Args:
            max_messages: Maximum number of messages to keep
        """
        if max_messages > 0:
            # Keep only the last max_messages
            self.redis_client.ltrim(self.key, -max_messages, -1)

    def get_total_tokens(self) -> int:
        """Calculate total tokens in conversation buffer.

        Returns:
            Total token count
        """
        messages = self.get_messages()
        return sum(msg.metadata.tokens for msg in messages)

    def clear(self) -> None:
        """Clear all messages in the conversation buffer."""
        self.redis_client.delete(self.key)


class ActiveContext:
    """Manages active context / scratchpad using Redis hash.

    Key naming: agent:stm:context:{session_id}
    Data structure: Hash
    Methods: HSET, HGETALL, HINCRBY
    """

    def __init__(self, session_id: str, redis_client: Optional[Redis] = None):
        """Initialize active context.

        Args:
            session_id: Unique session identifier
            redis_client: Redis client instance (uses db_manager if not provided)
        """
        self.session_id = session_id
        self.redis_client = redis_client or db_manager.connect_redis()
        self.key = f"agent:stm:context:{session_id}"

    def initialize(self, ttl: Optional[int] = None) -> None:
        """Initialize context with default values.

        Args:
            ttl: Time to live in seconds
        """
        current_time = int(time.time())
        context = ActiveContextData(
            total_tokens=0,
            created_at=current_time,
            updated_at=current_time,
        )
        self._update_hash(context.model_dump(exclude_none=True))
        if ttl:
            self.redis_client.expire(self.key, ttl)

    def update_field(
        self,
        field: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> None:
        """Update a specific field in the context.

        Args:
            field: Field name to update
            value: New value
            ttl: Time to live in seconds (resets TTL if provided)
        """
        # Update the field
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        self.redis_client.hset(self.key, field, str(value))

        # Update updated_at timestamp
        self.redis_client.hset(self.key, "updated_at", int(time.time()))

        # Reset TTL on interaction
        if ttl:
            self.redis_client.expire(self.key, ttl)

    def get_context(self) -> ActiveContextData:
        """Retrieve the entire context.

        Returns:
            ActiveContextData object
        """
        context_dict = self.redis_client.hgetall(self.key)
        if not context_dict:
            return ActiveContextData()

        # Parse JSON fields
        for key in ["extracted_entities"]:
            if key in context_dict and context_dict[key]:
                try:
                    context_dict[key] = json.loads(context_dict[key])
                except (json.JSONDecodeError, TypeError):
                    pass

        # Convert numeric fields
        for key in ["total_tokens", "created_at", "updated_at"]:
            if key in context_dict and context_dict[key]:
                try:
                    context_dict[key] = int(context_dict[key])
                except (ValueError, TypeError):
                    context_dict[key] = 0

        return ActiveContextData(**context_dict)

    def increment_tokens(self, amount: int, ttl: Optional[int] = None) -> int:
        """Increment token count.

        Args:
            amount: Amount to increment (can be negative)
            ttl: Time to live in seconds (resets TTL if provided)

        Returns:
            New token count
        """
        new_total = self.redis_client.hincrby(self.key, "total_tokens", amount)
        self.redis_client.hset(self.key, "updated_at", int(time.time()))

        if ttl:
            self.redis_client.expire(self.key, ttl)

        return new_total

    def set_current_goal(self, goal: str, ttl: Optional[int] = None) -> None:
        """Set current goal.

        Args:
            goal: Goal description
            ttl: Time to live in seconds
        """
        self.update_field("current_goal", goal, ttl)

    def set_extracted_entities(self, entities: Dict[str, Any], ttl: Optional[int] = None) -> None:
        """Set extracted entities.

        Args:
            entities: Dictionary of extracted entities
            ttl: Time to live in seconds
        """
        self.update_field("extracted_entities", entities, ttl)

    def set_last_tool_used(self, tool_name: str, ttl: Optional[int] = None) -> None:
        """Set last tool used.

        Args:
            tool_name: Name of the tool
            ttl: Time to live in seconds
        """
        self.update_field("last_tool_used", tool_name, ttl)

    def set_user_mood(self, mood: str, ttl: Optional[int] = None) -> None:
        """Set user mood.

        Args:
            mood: User mood description
            ttl: Time to live in seconds
        """
        self.update_field("user_mood", mood, ttl)

    def _update_hash(self, data: Dict[str, Any]) -> None:
        """Internal method to update hash with dictionary.

        Args:
            data: Dictionary of field-value pairs
        """
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            self.redis_client.hset(self.key, key, str(value))

    def clear(self) -> None:
        """Clear all context data."""
        self.redis_client.delete(self.key)


class RedisMemoryManager:
    """High-level manager for Redis short-term memory.

    Combines ConversationBuffer and ActiveContext with TTL management.
    """

    def __init__(
        self,
        session_id: str,
        default_ttl: int = 3600,
        redis_client: Optional[Redis] = None,
    ):
        """Initialize Redis memory manager.

        Args:
            session_id: Unique session identifier
            default_ttl: Default time to live in seconds (default: 1 hour)
            redis_client: Redis client instance
        """
        self.session_id = session_id
        self.default_ttl = default_ttl
        self.redis_client = redis_client or db_manager.connect_redis()
        self.conversation = ConversationBuffer(session_id, self.redis_client)
        self.context = ActiveContext(session_id, self.redis_client)

    def reset_ttl(self) -> None:
        """Reset TTL for both conversation and context."""
        self.redis_client.expire(self.conversation.key, self.default_ttl)
        self.redis_client.expire(self.context.key, self.default_ttl)

    def add_interaction(
        self,
        role: str,
        content: str,
        tokens: int = 0,
        intent: Optional[str] = None,
    ) -> None:
        """Add a new interaction (message + TTL reset).

        Args:
            role: Message role
            content: Message content
            tokens: Token count
            intent: Detected intent
        """
        self.conversation.add_message(
            role=role, content=content, tokens=tokens, intent=intent, ttl=self.default_ttl
        )
        self.reset_ttl()

    def update_context_field(self, field: str, value: Any) -> None:
        """Update context field and reset TTL.

        Args:
            field: Field name
            value: Field value
        """
        self.context.update_field(field, value, ttl=self.default_ttl)
        self.reset_ttl()

    def get_conversation_history(
        self, max_messages: Optional[int] = None
    ) -> List[ConversationMessage]:
        """Get conversation history, optionally trimmed.

        Args:
            max_messages: Maximum number of messages to return

        Returns:
            List of conversation messages
        """
        if max_messages:
            self.conversation.trim_conversation(max_messages)
        return self.conversation.get_messages()

    def clear_all(self) -> None:
        """Clear both conversation and context."""
        self.conversation.clear()
        self.context.clear()
