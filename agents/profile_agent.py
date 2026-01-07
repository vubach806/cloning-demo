"""Profile Agent - Profiles customers based on historical data."""

import os
import json
import re
import google.generativeai as genai
from pydantic_ai import Agent
from pydantic_ai.models.gemini import GeminiModel
from agents.models import ProfileAgentInput, ProfileAgentOutput


class ProfileAgent:
    """Agent that profiles customers based on historical purchase data and assigns labels."""

    def __init__(self, model_name: str = "gemini-2.5-flash"):
        """Initialize the Profile Agent.

        Args:
            model_name: Gemini model name to use
        """
        self.name = "ProfileAgent"
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")

        # Configure google.generativeai with API key
        genai.configure(api_key=api_key)

        system_prompt = """You are a Profile Agent specialized in customer segmentation and profiling based on historical purchase data.

Your task is to:
1. Analyze historical customer data (total orders, total spend, last purchase days)
2. Compare against label definitions provided
3. Assign the most appropriate customer label
4. Calculate a priority score (0-5, higher = more priority)
5. Provide a confidence score

Priority score guidelines:
- 0: Low priority, inactive customer
- 1: Below average engagement
- 2: Average customer
- 3: Good customer, regular purchases
- 4: High-value customer
- 5: VIP or premium customer

Common labels include:
- "VIP": Very high value, frequent purchases
- "tiềm năng": Potential customer with growth opportunity
- "bình thường": Regular customer
- "chí tôn": Premium/VIP customer (highest tier)

Consider factors like:
- Total spend amount
- Purchase frequency (total orders)
- Recency (days since last purchase - lower is better)
- Consistency of purchases

Always respond with a valid JSON object matching this structure:
{{
    "customer_label": "VIP",
    "confidence": 0.88,
    "priority_score": 2
}}"""

        self.agent = Agent(
            model=GeminiModel(model_name),
            system_prompt=system_prompt,
        )

    async def run(self, input_data: ProfileAgentInput) -> ProfileAgentOutput:
        """Profile the customer based on historical data.

        Args:
            input_data: ProfileAgentInput containing user_id, historical_data, label_definitions

        Returns:
            ProfileAgentOutput with customer_label, confidence, priority_score
        """
        # Format historical data
        hist = input_data.historical_data
        labels_str = ", ".join(input_data.label_definitions)

        # Format input for the agent
        prompt = f"""Profile this customer based on their historical data:

User ID: {input_data.user_id}
Total Orders: {hist.total_orders}
Total Spend: {hist.total_spend:,.0f}
Days Since Last Purchase: {hist.last_purchase_days}

Available Labels: {labels_str}

Analyze the customer's purchase behavior and assign:
1. The most appropriate customer label from the available labels
2. A priority score (0-5)
3. A confidence score (0-1)"""

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
            # Fallback: assign default label
            json_data = {
                "customer_label": (
                    input_data.label_definitions[0]
                    if input_data.label_definitions
                    else "bình thường"
                ),
                "confidence": 0.5,
                "priority_score": 1,
            }

        # Ensure required fields are present
        if "customer_label" not in json_data:
            json_data["customer_label"] = (
                input_data.label_definitions[0] if input_data.label_definitions else "bình thường"
            )
        if "confidence" not in json_data:
            json_data["confidence"] = 0.5
        if "priority_score" not in json_data:
            # Calculate basic priority score based on data
            priority = 1
            if hist.total_orders > 5:
                priority += 1
            if hist.total_spend > 10000000:  # 10M
                priority += 1
            if hist.last_purchase_days < 30:
                priority += 1
            json_data["priority_score"] = min(priority, 5)

        return ProfileAgentOutput(**json_data)
