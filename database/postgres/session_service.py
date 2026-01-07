"""Service for managing sessions in PostgreSQL (Episodic Memory)."""

from typing import Optional, Dict, Any
import uuid
from sqlalchemy.orm import Session
from database.postgres.models import Session as SessionModel
from database.postgres.client import get_postgres_session


def update_handoff_reason(
    session_id: str,
    handoff_reason: Optional[str],
    db_session: Optional[Session] = None,
) -> SessionModel:
    """Update session with handoff reason.

    Args:
        session_id: Session UUID identifier
        handoff_reason: Reason for handoff (can be None)
        db_session: Database session (uses default if not provided)

    Returns:
        Session object
    """
    if db_session is None:
        db_session = get_postgres_session()

    # Convert session_id to UUID if it's a string
    try:
        session_uuid = uuid.UUID(session_id) if isinstance(session_id, str) else session_id
    except ValueError:
        raise ValueError(f"Invalid session_id format: {session_id}")

    # Try to find existing session
    session = db_session.query(SessionModel).filter(SessionModel.id == session_uuid).first()

    if session:
        # Update existing session
        session.handoff_reason = handoff_reason
    else:
        # Create new session if not exists
        session = SessionModel(
            id=session_uuid,
            user_id=uuid.uuid4(),  # Default user_id, should be provided
            handoff_reason=handoff_reason,
        )
        db_session.add(session)

    db_session.commit()
    db_session.refresh(session)
    return session


def get_or_create_session(
    session_id: str,
    user_id: str,
    title: Optional[str] = None,
    db_session: Optional[Session] = None,
) -> SessionModel:
    """Get existing session or create new one.

    Args:
        session_id: Session UUID identifier (string or UUID)
        user_id: User identifier (string or UUID) - can be non-UUID string
        title: Optional session title
        db_session: Database session (uses default if not provided)

    Returns:
        Session object
    """
    if db_session is None:
        db_session = get_postgres_session()

    # Convert session_id to UUID
    try:
        session_uuid = uuid.UUID(session_id) if isinstance(session_id, str) else session_id
    except ValueError:
        raise ValueError(f"Invalid session_id format (must be UUID): {session_id}")

    # Try to convert user_id to UUID, but allow non-UUID strings
    # If user_id is not a valid UUID, we'll need to handle it differently
    # For now, let's try to convert and if it fails, we'll use a default UUID
    try:
        user_uuid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
    except (ValueError, AttributeError):
        # If user_id is not a valid UUID, generate a deterministic UUID from the string
        # This allows non-UUID user_ids to work
        user_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, str(user_id))

    # Try to find existing session
    session = db_session.query(SessionModel).filter(SessionModel.id == session_uuid).first()

    if not session:
        # Create new session
        session = SessionModel(
            id=session_uuid,
            user_id=user_uuid,
            title=title,
        )
        db_session.add(session)
        db_session.commit()
        db_session.refresh(session)

    return session


def update_session_handoff(
    session_id: str,
    handoff_reason: Optional[str],
    current_stage_id: Optional[int] = None,
    metadata: Optional[Dict[str, Any]] = None,
    db_session: Optional[Session] = None,
) -> SessionModel:
    """Update session with handoff information.

    Args:
        session_id: Session UUID identifier
        handoff_reason: Reason for handoff
        current_stage_id: Current stage ID (FK to sales_pipelines)
        metadata: Optional metadata to update
        db_session: Database session (uses default if not provided)

    Returns:
        Session object
    """
    if db_session is None:
        db_session = get_postgres_session()

    try:
        session_uuid = uuid.UUID(session_id) if isinstance(session_id, str) else session_id
    except ValueError:
        raise ValueError(f"Invalid session_id format: {session_id}")

    session = db_session.query(SessionModel).filter(SessionModel.id == session_uuid).first()

    if not session:
        raise ValueError(f"Session not found: {session_id}")

    # Update fields
    if handoff_reason is not None:
        session.handoff_reason = handoff_reason
    if current_stage_id is not None:
        session.current_stage_id = current_stage_id
    if metadata is not None:
        if session.session_metadata:
            session.session_metadata.update(metadata)
        else:
            session.session_metadata = metadata

    db_session.commit()
    db_session.refresh(session)
    return session


def get_session(
    session_id: str,
    db_session: Optional[Session] = None,
) -> Optional[SessionModel]:
    """Get session by session_id.

    Args:
        session_id: Session UUID identifier
        db_session: Database session (uses default if not provided)

    Returns:
        Session object or None if not found
    """
    if db_session is None:
        db_session = get_postgres_session()

    try:
        session_uuid = uuid.UUID(session_id) if isinstance(session_id, str) else session_id
    except ValueError:
        return None

    return db_session.query(SessionModel).filter(SessionModel.id == session_uuid).first()
