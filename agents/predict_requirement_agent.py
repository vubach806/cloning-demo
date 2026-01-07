"""Predict Customer Requirement Agent - Predicts explicit and implicit customer requirements."""

import os
import json
import re
import google.generativeai as genai
from pydantic_ai import Agent
from pydantic_ai.models.gemini import GeminiModel
from agents.models import PredictRequirementInput, PredictRequirementOutput


class PredictRequirementAgent:
    """Agent that predicts customer requirements from messages and conversation history."""

    def __init__(self, model_name: str = "gemini-2.5-flash"):
        """Initialize the Predict Requirement Agent.

        Args:
            model_name: Gemini model name to use
        """
        self.name = "PredictRequirementAgent"
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")

        # Configure google.generativeai with API key
        genai.configure(api_key=api_key)

        system_prompt = """You are a Predict Customer Requirement Agent specialized in analyzing customer messages and conversation history to extract both explicit and implicit requirements.

Your task is to:
1. Analyze the latest message and conversation history
2. Identify explicit requirements (directly stated or clearly inferred)
3. Infer implicit requirements (not explicitly stated but logically implied)
4. Classify the service type

Explicit requirements are things the customer directly mentions or clearly wants.
Implicit requirements are logical inferences based on context, such as:
- Capacity needs based on family size mentioned
- Budget constraints based on price discussions
- Usage patterns based on lifestyle mentions
- Quality expectations based on product type

Service types include:
- product_purchase: Customer wants to buy a product
- consultation: Customer needs advice or consultation
- support: Customer needs technical support
- upgrade: Customer wants to upgrade existing product
- replacement: Customer wants to replace something
- information: Customer seeks information

Always respond with a valid JSON object matching this structure:
{{
    "explicit_requirements": ["requirement1", "requirement2"],
    "implicit_requirements": ["requirement1", "requirement2"],
    "service_type": "product_purchase"
}}"""

        self.agent = Agent(
            model=GeminiModel(model_name),
            system_prompt=system_prompt,
        )

    async def run(self, input_data: PredictRequirementInput) -> PredictRequirementOutput:
        """Predict customer requirements.

        Args:
            input_data: PredictRequirementInput containing latest_message, short_memory, sales_node

        Returns:
            PredictRequirementOutput with explicit_requirements, implicit_requirements, service_type
        """
        # Format conversation history
        memory_text = ""
        if input_data.short_memory:
            memory_text = "\n\nRecent conversation history:\n"
            for i, msg in enumerate(input_data.short_memory[-20:], 1):  # Last 20 messages
                if isinstance(msg, dict):
                    role = msg.get("role", "unknown")
                    content = msg.get("content", "")
                    memory_text += f"{i}. [{role}]: {content}\n"
                else:
                    memory_text += f"{i}. {msg}\n"

        # Format input for the agent
        prompt = f"""Analyze the customer message and predict their requirements:

Latest Message: {input_data.latest_message}
Current Sales Node: {input_data.sales_node}
{memory_text}

Extract explicit requirements (directly stated), implicit requirements (logically inferred), and classify the service type."""

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
                "explicit_requirements": [],
                "implicit_requirements": [],
                "service_type": "information",
            }

        # Ensure lists are present
        if "explicit_requirements" not in json_data:
            json_data["explicit_requirements"] = []
        if "implicit_requirements" not in json_data:
            json_data["implicit_requirements"] = []
        if "service_type" not in json_data:
            json_data["service_type"] = "information"

        return PredictRequirementOutput(**json_data)
