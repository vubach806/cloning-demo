"""Memory Manager - Handles input reception and memory management."""

import asyncio
from typing import Optional, Dict, Any, Literal
from datetime import datetime
from database.redis import RedisMemoryManager
from database.postgres.models import Message as MessageModel
from database.postgres.client import get_postgres_session
from database.postgres.session_service import get_session, update_session_handoff
from database.debug import is_debug_enabled
from workflow.debug import (
    print_memory_input,
    print_sliding_window,
    print_summary_trigger,
    print_user_info_extraction,
    print_conversation_summary,
    print_active_context,
)
import uuid


class MemoryManager:
    """Manages memory: conversation buffer, active context, and message storage."""

    def __init__(
        self,
        session_id: str,
        max_buffer_messages: int = 50,
        default_ttl: int = 3600,
    ):
        """Initialize memory manager.

        Args:
            session_id: Session identifier
            max_buffer_messages: Maximum messages in buffer before sliding window (default: 50)
            default_ttl: Default TTL for Redis keys (default: 3600 seconds)
        """
        self.session_id = session_id
        self.max_buffer_messages = max_buffer_messages
        self.redis_memory = RedisMemoryManager(
            session_id=session_id,
            default_ttl=default_ttl,
        )

    async def receive_input(
        self,
        role: Literal["user", "assistant", "system", "tool"],
        content: str,
        tokens: int = 0,
        intent: Optional[str] = None,
        tool_calls: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Receive and process input from user, agent, or tool.

        Args:
            role: Message role (user, assistant, system, tool)
            content: Message content
            tokens: Token count for the message
            intent: Detected intent (optional)
            tool_calls: Tool calls if role is assistant (optional)
            metadata: Additional metadata (optional)
        """
        # Debug: Print input reception
        print_memory_input(role=role, content=content, tokens=tokens, intent=intent)

        # Prepare metadata
        message_metadata = {
            "tokens": tokens,
            "intent": intent,
        }
        if metadata:
            message_metadata.update(metadata)

        # Add to conversation buffer (Redis)
        self.redis_memory.add_interaction(
            role=role,
            content=content,
            tokens=tokens,
            intent=intent,
        )

        # Update active context based on role
        if role == "user":
            # Update user mood and entities in parallel (simulated)
            # In real implementation, you might want to analyze user input here
            pass

        # Check if we need to apply sliding window
        messages = self.redis_memory.get_conversation_history()
        if len(messages) > self.max_buffer_messages:
            await self._apply_sliding_window()

        # Check if we need to trigger summary (after 50 messages saved to PostgreSQL)
        await self._check_and_trigger_summary()

    async def _apply_sliding_window(self) -> None:
        """Apply sliding window: move old messages to PostgreSQL."""
        # Get all messages from buffer
        messages = self.redis_memory.get_conversation_history()

        # Keep only the most recent messages in buffer
        keep_count = self.max_buffer_messages // 2  # Keep half
        old_messages = messages[:-keep_count]
        new_messages = messages[-keep_count:]

        # Save old messages to PostgreSQL
        saved_count = 0
        if old_messages:
            await self._save_messages_to_postgres(old_messages)
            saved_count = len(old_messages)

        # Debug: Print sliding window operation
        print_sliding_window(
            old_count=len(old_messages),
            kept_count=keep_count,
            saved_count=saved_count,
        )

        # Trim buffer to keep only recent messages
        self.redis_memory.conversation.trim_conversation(keep_count)

    async def _save_messages_to_postgres(self, messages: list) -> None:
        """Save messages to PostgreSQL messages table.

        Args:
            messages: List of ConversationMessage objects
        """
        db_session = get_postgres_session()
        try:
            # Convert session_id to UUID
            try:
                session_uuid = (
                    uuid.UUID(self.session_id)
                    if isinstance(self.session_id, str)
                    else self.session_id
                )
            except ValueError:
                # If session_id is not valid UUID, skip saving
                return

            message_objects = []
            for msg in messages:
                # Extract tool_calls from metadata if exists
                tool_calls = None
                if hasattr(msg, "metadata") and msg.metadata:
                    # Check if there are tool calls in metadata
                    if isinstance(msg.metadata, dict) and "tool_calls" in msg.metadata:
                        tool_calls = msg.metadata["tool_calls"]

                message_obj = MessageModel(
                    session_id=session_uuid,
                    role=msg.role,
                    content=msg.content,
                    tool_calls=tool_calls,
                    token_count=msg.metadata.tokens if hasattr(msg.metadata, "tokens") else 0,
                    created_at=datetime.fromtimestamp(msg.timestamp),
                )
                message_objects.append(message_obj)

            db_session.add_all(message_objects)
            db_session.commit()

            if is_debug_enabled():
                print(f"💾 Saved {len(message_objects)} messages to PostgreSQL")
        except Exception as e:
            db_session.rollback()
            if is_debug_enabled():
                print(f"⚠️  Error saving messages to PostgreSQL: {e}")
        finally:
            db_session.close()

    def update_active_context(
        self,
        current_goal: Optional[str] = None,
        extracted_entities: Optional[Dict[str, Any]] = None,
        last_tool_used: Optional[str] = None,
        user_mood: Optional[str] = None,
    ) -> None:
        """Update active context fields.

        Args:
            current_goal: Current goal
            extracted_entities: Extracted entities
            last_tool_used: Last tool used
            user_mood: User mood
        """
        if current_goal is not None:
            self.redis_memory.context.set_current_goal(current_goal)
        if extracted_entities is not None:
            self.redis_memory.context.set_extracted_entities(extracted_entities)
        if last_tool_used is not None:
            self.redis_memory.context.set_last_tool_used(last_tool_used)
        if user_mood is not None:
            self.redis_memory.context.set_user_mood(user_mood)

    def get_conversation_history(self, max_messages: Optional[int] = None) -> list:
        """Get conversation history.

        Args:
            max_messages: Maximum number of messages to return

        Returns:
            List of conversation messages
        """
        return self.redis_memory.get_conversation_history(max_messages=max_messages)

    def get_active_context(self) -> Dict[str, Any]:
        """Get active context.

        Returns:
            Active context data
        """
        context = self.redis_memory.context.get_context()
        context_dict = context.model_dump()

        # Debug: Print active context
        print_active_context(context_dict)

        return context_dict

    async def _check_and_trigger_summary(self) -> None:
        """Check if we need to trigger summary agents (after 50 messages)."""
        # Count messages in PostgreSQL for this session
        db_session = get_postgres_session()
        try:
            try:
                session_uuid = (
                    uuid.UUID(self.session_id)
                    if isinstance(self.session_id, str)
                    else self.session_id
                )
            except ValueError:
                return

            from sqlalchemy import text

            result = db_session.execute(
                text("SELECT COUNT(*) FROM messages WHERE session_id = :session_id"),
                {"session_id": session_uuid},
            )
            message_count = result.scalar()

            # Trigger summary after 50 messages
            if message_count >= 50 and message_count % 50 == 0:
                print_summary_trigger(message_count)
                await self._trigger_summary_agents()
        except Exception as e:
            if is_debug_enabled():
                print(f"⚠️  Error checking message count: {e}")
        finally:
            db_session.close()

    async def _trigger_summary_agents(self) -> None:
        """Trigger summary agents to extract user info and update session summary."""
        from agents.summary_agent import SummaryAgent
        from database.postgres.session_service import get_session

        summary_agent = SummaryAgent()

        # Get messages from PostgreSQL
        db_session = get_postgres_session()
        try:
            try:
                session_uuid = (
                    uuid.UUID(self.session_id)
                    if isinstance(self.session_id, str)
                    else self.session_id
                )
            except ValueError:
                return

            # Get last 50 messages
            messages = (
                db_session.query(MessageModel)
                .filter(MessageModel.session_id == session_uuid)
                .order_by(MessageModel.created_at.desc())
                .limit(50)
                .all()
            )

            # Convert to dict format
            messages_dict = [
                {
                    "role": msg.role,
                    "content": msg.content,
                    "tool_calls": msg.tool_calls,
                    "created_at": msg.created_at.isoformat(),
                }
                for msg in reversed(messages)  # Reverse to get chronological order
            ]

            # Get session to retrieve old summary
            session = get_session(self.session_id)
            old_summary = None
            if session and session.session_metadata:
                old_summary = session.session_metadata.get("summary")

            # Run both summary tasks in parallel
            user_info_task = summary_agent.extract_user_information(messages_dict)
            summary_task = summary_agent.summarize_conversation(messages_dict, old_summary)

            user_info, summary_result = await asyncio.gather(
                user_info_task,
                summary_task,
            )

            # Debug: Print extracted user info
            print_user_info_extraction(user_info)

            # Update customer information (if user info extracted)
            if user_info and any(
                [user_info.get("name"), user_info.get("phone"), user_info.get("email")]
            ):
                await self._update_customer_info(user_info)

            # Debug: Print conversation summary
            if summary_result:
                print_conversation_summary(
                    summary=summary_result.get("summary", ""),
                    tags=summary_result.get("tags", []),
                    key_topics=summary_result.get("key_topics", []),
                    is_update=old_summary is not None,
                )

            # Update session summary
            if summary_result:
                await self._update_session_summary(summary_result)

            # Delete old messages after summary
            await self._delete_old_messages(session_uuid)

        except Exception as e:
            if is_debug_enabled():
                print(f"⚠️  Error in summary agents: {e}")
        finally:
            db_session.close()

    async def _update_customer_info(self, user_info: Dict[str, Any]) -> None:
        """Update customer information in PostgreSQL.

        Args:
            user_info: Extracted user information
        """
        from database.postgres.models import Customer
        from database.postgres.client import get_postgres_session

        db_session = get_postgres_session()
        try:
            # Get session to find user_id and shop_id
            session = get_session(self.session_id)
            if not session:
                return

            # Try to find existing customer or create new
            customer = db_session.query(Customer).filter(Customer.id == session.user_id).first()

            if customer:
                # Update existing customer
                if user_info.get("name"):
                    customer.full_name = user_info["name"]
                if user_info.get("phone"):
                    customer.phone = user_info["phone"]
                if user_info.get("email"):
                    customer.email = user_info["email"]
                if user_info.get("preferences"):
                    if customer.preferences:
                        customer.preferences.update(user_info["preferences"])
                    else:
                        customer.preferences = user_info["preferences"]
            else:
                # Create new customer (if we have shop_id)
                # Note: This requires shop_id, which might not be available
                # For now, skip creation if no shop_id
                pass

            db_session.commit()
            if is_debug_enabled():
                print(f"✅ Updated customer information")
        except Exception as e:
            db_session.rollback()
            if is_debug_enabled():
                print(f"⚠️  Error updating customer info: {e}")
        finally:
            db_session.close()

    async def _update_session_summary(self, summary_result: Dict[str, Any]) -> None:
        """Update session summary in PostgreSQL.

        Args:
            summary_result: Summary result with summary, tags, key_topics
        """
        try:
            session = get_session(self.session_id)
            if not session:
                return

            # Get existing metadata or create new
            metadata = session.session_metadata or {}
            metadata["summary"] = summary_result.get("summary", "")
            if summary_result.get("tags"):
                metadata["tags"] = summary_result["tags"]
            if summary_result.get("key_topics"):
                metadata["key_topics"] = summary_result["key_topics"]

            # Update session
            update_session_handoff(
                session_id=self.session_id,
                handoff_reason=None,  # Don't change handoff_reason
                metadata=metadata,
            )

            if is_debug_enabled():
                print(f"✅ Updated session summary")
        except Exception as e:
            if is_debug_enabled():
                print(f"⚠️  Error updating session summary: {e}")

    async def _delete_old_messages(self, session_uuid: uuid.UUID) -> None:
        """Delete old messages from PostgreSQL after summary.

        Args:
            session_uuid: Session UUID
        """
        from sqlalchemy import text
        from database.postgres.client import get_postgres_session

        db_session = get_postgres_session()
        try:
            # Delete messages older than the last 50 (keep recent ones)
            db_session.execute(
                text(
                    """
                    DELETE FROM messages 
                    WHERE session_id = :session_id 
                    AND id NOT IN (
                        SELECT id FROM messages 
                        WHERE session_id = :session_id 
                        ORDER BY created_at DESC 
                        LIMIT 50
                    )
                """
                ),
                {"session_id": session_uuid},
            )
            db_session.commit()
            if is_debug_enabled():
                print(f"🗑️  Deleted old messages (kept last 50)")
        except Exception as e:
            db_session.rollback()
            if is_debug_enabled():
                print(f"⚠️  Error deleting old messages: {e}")
        finally:
            db_session.close()
