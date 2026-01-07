"""Orchestrator Agent - Determines task based on intent and handoff analysis."""

import os
import json
import re
import google.generativeai as genai
from pydantic_ai import Agent
from pydantic_ai.models.gemini import GeminiModel
from agents.models import OrchestratorAgentInput, OrchestratorAgentOutput


class OrchestratorAgent:
    """Agent that orchestrates tasks based on intent and handoff analysis."""

    def __init__(self, model_name: str = "gemini-2.5-flash"):
        """Initialize the Orchestrator Agent.

        Args:
            model_name: Gemini model name to use
        """
        self.name = "OrchestratorAgent"
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")

        # Configure google.generativeai with API key
        genai.configure(api_key=api_key)

        system_prompt = """You are an Orchestrator Agent that determines the appropriate task based on user intent and handoff analysis.

Your task is to:
1. Analyze the intent and handoff analysis results
2. Determine the appropriate task:
   - "sales_task": For purchase consultations, product inquiries, bookings, etc. that can be handled by the system
   - "human_handle": When handoff_required is true, or risk_level is high/medium, or policy flags are raised
3. Provide a clear reason for the task selection

Task selection rules:
- If handoff_required is true → "human_handle"
- If risk_level is "high" or "medium" → "human_handle"
- If any policy flag (legal, medical, financial_risk, high_technical) is true → "human_handle"
- If intent_code is "purchase_consultation", "product_inquiry", "booking" and no handoff needed → "sales_task"
- If intent_code is "complaint" and emotion scores show high frustration/anger → "human_handle"
- Otherwise, analyze based on context and choose appropriately

Always respond with a valid JSON object matching this structure:
{{
    "user_id": "string",
    "task": "sales_task" or "human_handle",
    "clean_intent_text": "string",
    "intent_code": "string",
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
    "task_reason": "string - explanation for task selection"
}}"""

        self.agent = Agent(
            model=GeminiModel(model_name),
            system_prompt=system_prompt,
        )

    async def run(self, input_data: OrchestratorAgentInput) -> OrchestratorAgentOutput:
        """Determine task based on intent and handoff analysis.

        Args:
            input_data: OrchestratorAgentInput containing intent and handoff results

        Returns:
            OrchestratorAgentOutput with selected task
        """
        # Format input for the agent
        prompt = f"""Analyze the following intent and handoff analysis to determine the appropriate task:

User ID: {input_data.user_id}
Intent: {input_data.clean_intent_text}
Intent Code: {input_data.intent_code}
Handoff Required: {input_data.handoff_required}
Risk Level: {input_data.risk_level}
Policy Flags: {input_data.policy_flags.model_dump()}
Emotion Scores: {input_data.emotion_score.model_dump()}
Handoff Reason: {input_data.handoff_reason}

Determine the task: "sales_task" or "human_handle" and provide reasoning."""

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
            # Fallback: create output from input data
            json_data = {
                "user_id": input_data.user_id,
                "task": "human_handle" if input_data.handoff_required else "sales_task",
                "clean_intent_text": input_data.clean_intent_text,
                "intent_code": input_data.intent_code,
                "policy_flags": input_data.policy_flags.model_dump(),
                "emotion_score": input_data.emotion_score.model_dump(),
                "handoff_required": input_data.handoff_required,
                "handoff_reason": input_data.handoff_reason,
                "risk_level": input_data.risk_level,
                "task_reason": "Fallback task selection",
            }

        # Ensure user_id matches input and include all required fields
        json_data["user_id"] = input_data.user_id
        if "clean_intent_text" not in json_data:
            json_data["clean_intent_text"] = input_data.clean_intent_text
        if "intent_code" not in json_data:
            json_data["intent_code"] = input_data.intent_code
        if "policy_flags" not in json_data:
            json_data["policy_flags"] = input_data.policy_flags.model_dump()
        if "emotion_score" not in json_data:
            json_data["emotion_score"] = input_data.emotion_score.model_dump()
        if "handoff_required" not in json_data:
            json_data["handoff_required"] = input_data.handoff_required
        if "risk_level" not in json_data:
            json_data["risk_level"] = input_data.risk_level

        return OrchestratorAgentOutput(**json_data)
