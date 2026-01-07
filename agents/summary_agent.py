"""Summary Agent - Extracts user information and summarizes conversations."""

import os
import json
import re
import google.generativeai as genai
from pydantic_ai import Agent
from pydantic_ai.models.gemini import GeminiModel
from typing import List, Dict, Any, Optional


class SummaryAgent:
    """Agent that extracts user information and summarizes conversations."""

    def __init__(self, model_name: str = "gemini-2.5-flash"):
        """Initialize the Summary Agent.

        Args:
            model_name: Gemini model name to use
        """
        self.name = "SummaryAgent"
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")

        # Configure google.generativeai with API key
        genai.configure(api_key=api_key)

        system_prompt = """You are a Summary Agent specialized in extracting user information and summarizing conversations.

Your tasks:
1. Extract user information from conversation messages (name, preferences, contact info, etc.)
2. Summarize conversations into concise summaries
3. Identify key topics and tags

Always respond with valid JSON format."""

        self.agent = Agent(
            model=GeminiModel(model_name),
            system_prompt=system_prompt,
        )

    async def extract_user_information(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract user information from conversation messages.

        Args:
            messages: List of message dictionaries

        Returns:
            Dictionary containing extracted user information
        """
        # Format messages for the agent
        messages_text = "\n".join(
            [f"{msg.get('role', 'unknown')}: {msg.get('content', '')}" for msg in messages]
        )

        prompt = f"""Extract user information from the following conversation messages:

{messages_text}

Extract:
- User name (if mentioned)
- Contact information (phone, email)
- Preferences
- Interests
- Any other relevant user information

Respond with JSON format:
{{
    "name": "string or null",
    "phone": "string or null",
    "email": "string or null",
    "preferences": {{}},
    "interests": [],
    "other_info": {{}}
}}"""

        result = await self.agent.run(prompt)
        response_text = str(result.output)

        # Parse JSON response
        try:
            if response_text.strip().startswith("{"):
                return json.loads(response_text)
            else:
                json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
        except (json.JSONDecodeError, ValueError):
            pass

        # Fallback
        return {
            "name": None,
            "phone": None,
            "email": None,
            "preferences": {},
            "interests": [],
            "other_info": {},
        }

    async def summarize_conversation(
        self,
        messages: List[Dict[str, Any]],
        old_summary: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Summarize conversation, optionally updating existing summary.

        Args:
            messages: List of message dictionaries
            old_summary: Previous summary (optional)

        Returns:
            Dictionary containing new summary and tags
        """
        # Format messages for the agent
        messages_text = "\n".join(
            [f"{msg.get('role', 'unknown')}: {msg.get('content', '')}" for msg in messages]
        )

        if old_summary:
            prompt = f"""Update the conversation summary based on new messages.

Old Summary:
{old_summary}

New Messages:
{messages_text}

Create an updated summary that incorporates the new information while maintaining context from the old summary.

Respond with JSON format:
{{
    "summary": "updated summary text",
    "tags": ["tag1", "tag2"],
    "key_topics": ["topic1", "topic2"]
}}"""
        else:
            prompt = f"""Summarize the following conversation:

{messages_text}

Create a concise summary and identify key topics and tags.

Respond with JSON format:
{{
    "summary": "summary text",
    "tags": ["tag1", "tag2"],
    "key_topics": ["topic1", "topic2"]
}}"""

        result = await self.agent.run(prompt)
        response_text = str(result.output)

        # Parse JSON response
        try:
            if response_text.strip().startswith("{"):
                return json.loads(response_text)
            else:
                json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
        except (json.JSONDecodeError, ValueError):
            pass

        # Fallback
        return {
            "summary": "No summary available",
            "tags": [],
            "key_topics": [],
        }
