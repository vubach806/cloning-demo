"""Chainlit application for multi-agent system demo."""

import os
import uuid
import chainlit as cl
from workflow.orchestrator import WorkflowOrchestrator


def _render_phase_trace(phase_trace: list[str]) -> str:
    lines = phase_trace or ["(no trace)"]
    return "\n".join([f"- {line}" for line in lines])


@cl.on_chat_start
async def start():
    """Initialize the chat session."""
    orchestrator = WorkflowOrchestrator()
    session_id = str(uuid.uuid4())
    user_id = f"user_{session_id[:8]}"

    cl.user_session.set("orchestrator", orchestrator)
    cl.user_session.set("session_id", session_id)
    cl.user_session.set("user_id", user_id)

    # Default: hide pipeline progress (end users don't need it).
    # This Chainlit version doesn't expose input widgets (Switch/Input/etc.),
    # so we control the panel by environment variable.
    show_progress = os.getenv("SHOW_PIPELINE_PROGRESS", "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "y",
        "on",
    }
    cl.user_session.set("show_pipeline_progress", show_progress)

    await cl.Message(
        content="Welcome to the Multi-Agent System! I can help you with intent understanding and analysis. How can I assist you today?",
    ).send()


@cl.on_message
async def main(message: cl.Message):
    """Handle incoming messages."""
    orchestrator = cl.user_session.get("orchestrator")
    session_id = cl.user_session.get("session_id", "")
    user_id = cl.user_session.get("user_id", "unknown")
    show_progress = bool(cl.user_session.get("show_pipeline_progress", False))

    # Show loading indicator
    msg = cl.Message(content="")
    await msg.send()

    try:
        # Process message through intent and handoff analysis
        results = await orchestrator.process_user_message(
            user_id=user_id,
            session_id=session_id,
            raw_message=message.content,
            language="vi",
        )

        phase_trace = results.get("phase_trace", [])
        final_text = results.get("final_response_text", "")

        # Update / show the right-side debug panel when enabled.
        # When disabled, keep the main chat clean.
        if show_progress:
            trace_md = _render_phase_trace(phase_trace)
            trace_block = (
                "<details>"
                "<summary><b>Pipeline progress</b></summary>"
                f"<pre>{trace_md}</pre>"
                "</details>"
            )
            await cl.Message(content=trace_block).send()

        msg.content = final_text
        await msg.update()

    except Exception as e:
        error_msg = f"An error occurred: {str(e)}"
        msg.content = error_msg
        await msg.update()
