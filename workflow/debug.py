"""Debug utilities for agent outputs and memory management."""

import os
import json
from typing import Dict, Any, Optional
from agents.models import IntentAgentOutput, AnalyseHandoffOutput


def is_debug_enabled() -> bool:
    """Check if debug mode is enabled.

    Returns:
        True if DEBUG environment variable is set to 'true' or '1'
    """
    debug = os.getenv("DEBUG", "false").lower()
    return debug in ("true", "1", "yes")


def print_intent_result(result: IntentAgentOutput) -> None:
    """Print Intent Agent result in a formatted way.

    Args:
        result: IntentAgentOutput to print
    """
    print("\n" + "=" * 80)
    print("🔍 INTENT AGENT RESULT")
    print("=" * 80)
    print(f"User ID:        {result.user_id}")
    print(f"Session Name:   {result.session_name or '(empty)'}")
    print(f"Clean Intent:   {result.clean_intent_text}")
    print(f"Intent Code:    {result.intent_code}")
    print(f"Confidence:     {result.confidence:.2%}")
    print("=" * 80 + "\n")


def print_handoff_result(result: AnalyseHandoffOutput) -> None:
    """Print Analyse Handoff Agent result in a formatted way.

    Args:
        result: AnalyseHandoffOutput to print
    """
    print("\n" + "=" * 80)
    print("📊 ANALYSE HANDOFF AGENT RESULT")
    print("=" * 80)
    print(f"User ID:           {result.user_id}")
    print(f"Handoff Required:  {'✅ YES' if result.handoff_required else '❌ NO'}")
    print(f"Risk Level:        {result.risk_level.upper()}")
    print(f"Confidence:        {result.confidence:.2%}")

    if result.handoff_reason:
        print(f"Handoff Reason:    {result.handoff_reason}")

    print("\n📋 Policy Flags:")
    flags = result.policy_flags.model_dump()
    for flag, value in flags.items():
        status = "✅" if value else "❌"
        print(f"  {status} {flag}: {value}")

    print("\n😊 Emotion Scores:")
    emotions = result.emotion_score.model_dump()
    for emotion, score in emotions.items():
        if score > 0.1:  # Only show significant emotions
            bar = "█" * int(score * 20)
            print(f"  {emotion:12s}: {score:.2f} {bar}")

    print("=" * 80 + "\n")


def print_orchestration_result(result: Dict[str, Any]) -> None:
    """Print Orchestration result in a formatted way.

    Args:
        result: Orchestration result dictionary
    """
    print("\n" + "=" * 80)
    print("🎯 ORCHESTRATOR AGENT RESULT")
    print("=" * 80)
    print(f"User ID:       {result.get('user_id', 'N/A')}")
    print(f"Task:          {result.get('task', 'N/A').upper()}")

    if result.get("task_reason"):
        print(f"Task Reason:   {result['task_reason']}")

    print("=" * 80 + "\n")


def print_agent_results(
    intent_result: IntentAgentOutput,
    handoff_result: AnalyseHandoffOutput,
    orchestration_result: Dict[str, Any] = None,
) -> None:
    """Print all agent results in a formatted way.

    Args:
        intent_result: Intent Agent output
        handoff_result: Analyse Handoff Agent output
        orchestration_result: Optional Orchestration result
    """
    if not is_debug_enabled():
        return

    print_intent_result(intent_result)
    print_handoff_result(handoff_result)

    if orchestration_result:
        print_orchestration_result(orchestration_result)


def print_json_debug(data: Dict[str, Any], label: str = "DEBUG") -> None:
    """Print JSON data in a formatted way.

    Args:
        data: Dictionary to print as JSON
        label: Label for the debug output
    """
    if not is_debug_enabled():
        return

    print(f"\n[{label}]")
    print(json.dumps(data, indent=2, ensure_ascii=False))
    print()


def print_memory_input(
    role: str,
    content: str,
    tokens: int = 0,
    intent: Optional[str] = None,
) -> None:
    """Print memory input reception.

    Args:
        role: Message role
        content: Message content
        tokens: Token count
        intent: Intent (optional)
    """
    if not is_debug_enabled():
        return

    print("\n" + "=" * 80)
    print(f"📥 MEMORY INPUT: {role.upper()}")
    print("=" * 80)
    print(f"Content:    {content[:100]}{'...' if len(content) > 100 else ''}")
    print(f"Tokens:     {tokens}")
    if intent:
        print(f"Intent:     {intent}")
    print("=" * 80 + "\n")


def print_sliding_window(
    old_count: int,
    kept_count: int,
    saved_count: int,
) -> None:
    """Print sliding window operation.

    Args:
        old_count: Number of old messages moved
        kept_count: Number of messages kept in buffer
        saved_count: Number of messages saved to PostgreSQL
    """
    if not is_debug_enabled():
        return

    print("\n" + "=" * 80)
    print("🪟 SLIDING WINDOW OPERATION")
    print("=" * 80)
    print(f"Old Messages Moved:  {old_count}")
    print(f"Messages Kept:       {kept_count}")
    print(f"Saved to PostgreSQL: {saved_count}")
    print("=" * 80 + "\n")


def print_summary_trigger(message_count: int) -> None:
    """Print summary trigger information.

    Args:
        message_count: Total message count that triggered summary
    """
    if not is_debug_enabled():
        return

    print("\n" + "=" * 80)
    print("📝 SUMMARY TRIGGER")
    print("=" * 80)
    print(f"Message Count: {message_count} (triggered at 50)")
    print("Running summary agents in parallel...")
    print("=" * 80 + "\n")


def print_user_info_extraction(user_info: Dict[str, Any]) -> None:
    """Print extracted user information.

    Args:
        user_info: Extracted user information dictionary
    """
    if not is_debug_enabled():
        return

    print("\n" + "=" * 80)
    print("👤 EXTRACTED USER INFORMATION")
    print("=" * 80)
    if user_info.get("name"):
        print(f"Name:       {user_info['name']}")
    if user_info.get("phone"):
        print(f"Phone:      {user_info['phone']}")
    if user_info.get("email"):
        print(f"Email:      {user_info['email']}")
    if user_info.get("preferences"):
        print(f"Preferences: {user_info['preferences']}")
    if user_info.get("interests"):
        print(f"Interests:   {user_info['interests']}")
    print("=" * 80 + "\n")


def print_conversation_summary(
    summary: str,
    tags: list,
    key_topics: list,
    is_update: bool = False,
) -> None:
    """Print conversation summary.

    Args:
        summary: Summary text
        tags: List of tags
        key_topics: List of key topics
        is_update: Whether this is an update to existing summary
    """
    if not is_debug_enabled():
        return

    print("\n" + "=" * 80)
    print(f"📄 CONVERSATION SUMMARY {'(UPDATED)' if is_update else '(NEW)'}")
    print("=" * 80)
    print(f"Summary:    {summary[:200]}{'...' if len(summary) > 200 else ''}")
    if tags:
        print(f"Tags:       {', '.join(tags)}")
    if key_topics:
        print(f"Key Topics: {', '.join(key_topics)}")
    print("=" * 80 + "\n")


def print_active_context(context: Dict[str, Any]) -> None:
    """Print active context information.

    Args:
        context: Active context dictionary
    """
    if not is_debug_enabled():
        return

    print("\n" + "=" * 80)
    print("🧠 ACTIVE CONTEXT")
    print("=" * 80)
    if context.get("current_goal"):
        print(f"Current Goal:      {context['current_goal']}")
    if context.get("extracted_entities"):
        print(f"Extracted Entities: {context['extracted_entities']}")
    if context.get("last_tool_used"):
        print(f"Last Tool Used:    {context['last_tool_used']}")
    print(f"Total Tokens:      {context.get('total_tokens', 0)}")
    if context.get("user_mood"):
        print(f"User Mood:         {context['user_mood']}")
    print("=" * 80 + "\n")
