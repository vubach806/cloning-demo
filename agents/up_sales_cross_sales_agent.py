"""Up Sales / Cross Sales Agent - Identifies up-sell and cross-sell opportunities."""

import os
import json
import re
import google.generativeai as genai
from pydantic_ai import Agent
from pydantic_ai.models.gemini import GeminiModel
from agents.models import UpSalesCrossSalesInput, UpSalesCrossSalesOutput


class UpSalesCrossSalesAgent:
    """Agent that identifies up-sell and cross-sell opportunities based on customer requirements and available combos."""

    def __init__(self, model_name: str = "gemini-2.5-flash"):
        """Initialize the Up Sales / Cross Sales Agent.

        Args:
            model_name: Gemini model name to use
        """
        self.name = "UpSalesCrossSalesAgent"
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")

        # Configure google.generativeai with API key
        genai.configure(api_key=api_key)

        system_prompt = """You are an Up Sales / Cross Sales Agent specialized in identifying opportunities to suggest product combos that meet customer requirements.

Your task is to:
1. Analyze customer requirements (explicit and implicit)
2. Review available product combos and their stock levels
3. Select the best combo that matches customer needs
4. Provide a clear reason for the selection

Considerations:
- Match explicit requirements first, then implicit requirements
- Prioritize combos with sufficient stock
- Consider value proposition and customer needs
- If no suitable combo exists, return null for selected_combo

Always respond with a valid JSON object matching this structure:
{{
    "selected_combo": "C01",
    "reason": "Đáp ứng nhu cầu tiết kiệm điện và còn đủ tồn kho",
    "response_text": ""
}}

Note: response_text is usually left empty as it will be used by the Sales Agent."""

        self.agent = Agent(
            model=GeminiModel(model_name),
            system_prompt=system_prompt,
        )

    async def run(self, input_data: UpSalesCrossSalesInput) -> UpSalesCrossSalesOutput:
        """Identify up-sell/cross-sell opportunities.

        Args:
            input_data: UpSalesCrossSalesInput containing requirements, available_combos, short_memory, summary_conversation

        Returns:
            UpSalesCrossSalesOutput with selected_combo, reason, response_text
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

        # Format available combos
        combos_text = ""
        for combo in input_data.available_combos:
            products_str = ", ".join(combo.products)
            combos_text += f"\n- Combo {combo.combo_id}: {products_str} (Stock: {combo.stock})"

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

        # Format summary
        summary_text = ""
        if input_data.summary_conversation:
            summary_text = f"\n\nConversation Summary:\n{input_data.summary_conversation}"

        # Format input for the agent
        prompt = f"""Analyze customer requirements and available combos to identify the best up-sell/cross-sell opportunity:

Explicit Requirements: {explicit_req}
Implicit Requirements: {implicit_req}

Available Combos:{combos_text}
{memory_text}{summary_text}

Select the best combo that matches the customer's needs. Consider:
1. How well the combo matches explicit and implicit requirements
2. Stock availability
3. Value proposition for the customer

If no suitable combo exists, set selected_combo to null."""

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
            # Fallback: no combo selected
            json_data = {
                "selected_combo": None,
                "reason": "Unable to parse response",
                "response_text": "",
            }

        # Ensure required fields are present
        if "selected_combo" not in json_data:
            json_data["selected_combo"] = None
        if "reason" not in json_data:
            json_data["reason"] = None
        if "response_text" not in json_data:
            json_data["response_text"] = ""

        return UpSalesCrossSalesOutput(**json_data)
