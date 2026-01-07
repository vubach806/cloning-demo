"""Intent Agent - Makes user's question more clearly."""

import os
import json
import re
import google.generativeai as genai
from pydantic_ai import Agent
from pydantic_ai.models.gemini import GeminiModel
from agents.models import IntentAgentInput, IntentAgentOutput


class IntentAgent:
    """Agent that extracts and clarifies user intent from raw messages."""

    def __init__(self, model_name: str = "gemini-2.5-flash"):
        """Initialize the Intent Agent.

        Args:
            model_name: Gemini model name to use
        """
        self.name = "IntentAgent"
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")

        # Configure google.generativeai with API key
        genai.configure(api_key=api_key)

        system_prompt = """You are an Intent Agent specialized in understanding and clarifying user intentions.

Your task is to:
1. Analyze the raw user message and extract the core intent
2. Clean and clarify the intent into a clear, concise statement
3. Classify the intent with an appropriate intent_code
4. Provide a confidence score (0.0 to 1.0)

Common intent codes include:
- purchase_consultation: User wants to buy or consult about products
- product_inquiry: User asks about product details
- complaint: User has a complaint
- support_request: User needs technical support
- information_request: User asks for general information
- booking: User wants to make a reservation
- cancellation: User wants to cancel something
- feedback: User provides feedback

Always respond with a valid JSON object matching this structure:
{{
    "user_id": "string",
    "session_name": "string",
    "clean_intent_text": "string - clear, concise intent description",
    "intent_code": "string - one of the intent codes above",
    "confidence": 0.0-1.0
}}"""

        self.agent = Agent(
            model=GeminiModel(model_name),
            system_prompt=system_prompt,
        )

    async def run(self, input_data: IntentAgentInput) -> IntentAgentOutput:
        """Process user input and extract intent.

        Args:
            input_data: IntentAgentInput containing user_id, session_id, raw_message, language

        Returns:
            IntentAgentOutput with clean_intent_text, intent_code, confidence
        """
        # Format input for the agent
        prompt = f"""Analyze this user message and extract the intent:

User ID: {input_data.user_id}
Session ID: {input_data.session_id}
Language: {input_data.language}
Raw Message: {input_data.raw_message}

Extract and clarify the user's intent. Provide a clean, concise intent text, classify it with an intent_code, and provide a confidence score."""

        result = await self.agent.run(prompt)

        # Parse JSON response and validate with Pydantic model
        response_text = str(result.output)

        # Try to extract JSON from response
        try:
            # Try to parse as JSON directly
            if response_text.strip().startswith("{"):
                json_data = json.loads(response_text)
            else:
                # Try to find JSON in the response
                json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
                if json_match:
                    json_data = json.loads(json_match.group())
                else:
                    raise ValueError("No JSON found in response")
        except (json.JSONDecodeError, ValueError):
            # Fallback: create output from text
            json_data = {
                "user_id": input_data.user_id,
                "session_name": input_data.session_id,
                "clean_intent_text": response_text,
                "intent_code": "unknown",
                "confidence": 0.5,
            }

        # Ensure user_id matches input
        json_data["user_id"] = input_data.user_id

        return IntentAgentOutput(**json_data)
