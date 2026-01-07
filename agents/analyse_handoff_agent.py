"""Analyse Handoff Agent - Calculates emotion score and determines if human handoff is needed."""

import os
import json
import re
import google.generativeai as genai
from pydantic_ai import Agent
from pydantic_ai.models.gemini import GeminiModel
from agents.models import AnalyseHandoffInput, AnalyseHandoffOutput


class AnalyseHandoffAgent:
    """Agent that analyzes emotions and determines if human handoff is required."""

    def __init__(self, model_name: str = "gemini-2.5-flash"):
        """Initialize the Analyse Handoff Agent.

        Args:
            model_name: Gemini model name to use
        """
        self.name = "AnalyseHandoffAgent"
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")

        # Configure google.generativeai with API key
        genai.configure(api_key=api_key)

        system_prompt = """You are an Analyse Handoff Agent specialized in analyzing user emotions and determining if a human handoff is required.

Your task is to:
1. Analyze the user's message for emotional content
2. Detect emotions: frustration, anger, sadness, joy, fear, neutral (scores 0.0-1.0)
3. Check for policy concerns: legal, medical, financial_risk, high_technical
4. Determine if human handoff is required based on:
   - High negative emotions (frustration > 0.7, anger > 0.5)
   - Policy flags (legal, medical, financial_risk, high_technical)
   - Complex issues that require human judgment
5. Assess risk level: low, medium, high
6. Provide confidence score (0.0 to 1.0)

Handoff should be required when:
- User shows high frustration or anger
- Legal, medical, or financial risks are present
- Technical issues are too complex
- User explicitly requests human assistance
- Risk level is medium or high

Always respond with a valid JSON object matching this structure:
{{
    "user_id": "string",
    "policy_flags": {{
        "legal": false,
        "medical": false,
        "financial_risk": false,
        "high_technical": false
    }},
    "emotion_score": {{
        "frustration": 0.0-1.0,
        "anger": 0.0-1.0,
        "sadness": 0.0-1.0,
        "joy": 0.0-1.0,
        "fear": 0.0-1.0,
        "neutral": 0.0-1.0
    }},
    "handoff_required": true/false,
    "handoff_reason": "string or null",
    "risk_level": "low/medium/high",
    "confidence": 0.0-1.0
}}"""

        self.agent = Agent(
            model=GeminiModel(model_name),
            system_prompt=system_prompt,
        )

    async def run(self, input_data: AnalyseHandoffInput) -> AnalyseHandoffOutput:
        """Analyze user message for emotions and handoff requirements.

        Args:
            input_data: AnalyseHandoffInput containing user_id, session_id, raw_message, language

        Returns:
            AnalyseHandoffOutput with emotion_score, policy_flags, handoff_required, etc.
        """
        # Format input for the agent
        prompt = f"""Analyze this user message for emotions and handoff requirements:

User ID: {input_data.user_id}
Session ID: {input_data.session_id}
Language: {input_data.language}
Raw Message: {input_data.raw_message}

Analyze the emotional content, check for policy concerns, and determine if human handoff is required."""

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
            # Fallback: create default output
            json_data = {
                "user_id": input_data.user_id,
                "policy_flags": {
                    "legal": False,
                    "medical": False,
                    "financial_risk": False,
                    "high_technical": False,
                },
                "emotion_score": {
                    "frustration": 0.0,
                    "anger": 0.0,
                    "sadness": 0.0,
                    "joy": 0.0,
                    "fear": 0.0,
                    "neutral": 1.0,
                },
                "handoff_required": False,
                "handoff_reason": None,
                "risk_level": "low",
                "confidence": 0.5,
            }

        # Ensure user_id matches input
        json_data["user_id"] = input_data.user_id

        return AnalyseHandoffOutput(**json_data)
