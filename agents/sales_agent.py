"""Sales Agent - Main conversational sales agent."""

import os
import json
import re
import google.generativeai as genai
from pydantic_ai import Agent
from pydantic_ai.models.gemini import GeminiModel
from agents.models import SalesAgentInput, SalesAgentOutput


class SalesAgent:
    """Agent that handles the main sales conversation flow."""

    def __init__(self, model_name: str = "gemini-2.5-flash"):
        """Initialize the Sales Agent.

        Args:
            model_name: Gemini model name to use
        """
        self.name = "SalesAgent"
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")

        # Configure google.generativeai with API key
        genai.configure(api_key=api_key)

        system_prompt = """You are a Sales Person specialized in conducting natural, effective sales conversations.

Your task is to:
1. Understand the customer's profile and current sales stage
2. Use customer requirements and selected combo (if available) to craft responses
3. Maintain appropriate tone based on tone_policy
4. Guide the conversation naturally toward closing
5. Predict what type of input you expect next from the customer

Tone policies:
- professional_warm: Professional but warm and friendly
- friendly: Casual and approachable
- formal: Very formal and respectful
- consultative: Advisory and helpful

Sales nodes include:
- greeting: Initial greeting
- need_discovery: Understanding customer needs
- solution_matching: Matching solutions to needs
- price_discussion: Discussing pricing
- objection_handling: Handling concerns
- closing: Finalizing the sale

Next expected input types:
- preference_clarification: Customer clarifying preferences
- price_inquiry: Customer asking about price
- product_question: Customer asking about product details
- objection: Customer raising concerns
- agreement: Customer agreeing to proceed
- rejection: Customer declining

Always respond with a valid JSON object matching this structure:
{{
    "response_text": "Your natural, conversational response in Vietnamese",
    "next_expected_input": "preference_clarification",
    "stay_in_sales_node": true
}}
Answer like a human, everytime you see a question bot or human, say you are a human.
"""

        self.agent = Agent(
            model=GeminiModel(model_name),
            system_prompt=system_prompt,
        )

    async def run(self, input_data: SalesAgentInput) -> SalesAgentOutput:
        """Generate sales conversation response.

        Args:
            input_data: SalesAgentInput containing customer_label, sales_node, requirements, selected_combo, tone_policy, short_memory

        Returns:
            SalesAgentOutput with response_text, next_expected_input, stay_in_sales_node
        """
        # Format requirements
        explicit_req = (
            ", ".join(input_data.requirements.explicit)
            if input_data.requirements.explicit
            else "None"
        )
        implicit_req = (
            ", ".join(input_data.requirements.implicit)
            if input_data.requirements.implicit
            else "None"
        )

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

        # Format combo info
        combo_text = ""
        if input_data.selected_combo:
            combo_text = (
                "\nSelected Combo: "
                f"{input_data.selected_combo.combo_id}"
                f"\nProducts: {', '.join(input_data.selected_combo.products)}"
                f"\nStock: {input_data.selected_combo.stock}"
                f"\nPrice: {input_data.selected_combo.price} VND"
            )

        # Format input for the agent
        prompt = f"""Generate a natural sales conversation response:

Customer Profile: {input_data.customer_label}
Current Sales Node: {input_data.sales_node}
Tone Policy: {input_data.tone_policy}

Explicit Requirements: {explicit_req}
Implicit Requirements: {implicit_req}
{combo_text}
{memory_text}

Craft a response that:
1. Addresses the customer's requirements naturally
2. Uses the selected combo if available (mention it naturally)
3. Matches the tone policy
4. Guides the conversation forward in the sales process
5. Predicts what the customer might say next

Respond in Vietnamese, naturally and conversationally."""

        # Expose the exact prompt for debugging/trace purposes.
        # (This is useful when the model hallucinates prices/stock.)
        input_data.debug_prompt = prompt

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
            # Fallback: create basic response
            json_data = {
                "response_text": "Xin chào! Tôi có thể giúp gì cho bạn?",
                "next_expected_input": "preference_clarification",
                "stay_in_sales_node": True,
            }

        # Ensure required fields are present
        if "response_text" not in json_data:
            json_data["response_text"] = "Xin chào! Tôi có thể giúp gì cho bạn?"
        if "next_expected_input" not in json_data:
            json_data["next_expected_input"] = "preference_clarification"
        if "stay_in_sales_node" not in json_data:
            json_data["stay_in_sales_node"] = True

        return SalesAgentOutput(**json_data)
