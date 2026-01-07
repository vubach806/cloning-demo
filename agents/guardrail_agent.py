"""Guardrail Agent - Validates and moderates content before storing in memory."""

import os
import json
import re
import google.generativeai as genai
from pydantic_ai import Agent
from pydantic_ai.models.gemini import GeminiModel
from agents.models import GuardrailInput, GuardrailOutput


class GuardrailAgent:
    """Agent that validates, moderates, and ensures compliance of content before memory storage."""

    def __init__(self, model_name: str = "gemini-2.5-flash"):
        """Initialize the Guardrail Agent.

        Args:
            model_name: Gemini model name to use
        """
        self.name = "GuardrailAgent"
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")

        # Configure google.generativeai with API key
        genai.configure(api_key=api_key)

        system_prompt = """You are a Guardrail Agent specialized in content validation, moderation, and compliance checking.

Your task is to:
1. Validate response text for accuracy, appropriateness, and compliance
2. Check product data accuracy if provided
3. Flag sales content that needs double-checking
4. Modify text if necessary to ensure compliance
5. Provide clear reasons for any modifications or rejections

Validation checks include:
- Content accuracy: Ensure information is correct and not misleading
- Business rules compliance: Follow company policies and guidelines
- Sales accuracy: Verify product claims, pricing, and availability
- Tone appropriateness: Ensure professional and respectful language
- Legal compliance: Avoid false claims, misleading statements
- Data consistency: Verify product data matches response text

If content is approved:
- Set approved to true
- Set modified_text to null (no changes needed)
- Set sales_doublecheck to true if sales-related content needs human review
- Set reason_recheck if double-check is needed

If content needs modification:
- Set approved to true (after modification)
- Set modified_text to the corrected version
- Set sales_doublecheck if still needs review
- Set reason_recheck with explanation

If content is rejected:
- Set approved to false
- Set modified_text to null or a safe alternative
- Set reason_recheck with rejection reason

Always respond with a valid JSON object matching this structure:
{{
    "approved": true,
    "modified_text": null,
    "sales_doublecheck": true,
    "reason_recheck": "Sales claims need verification"
}}"""

        self.agent = Agent(
            model=GeminiModel(model_name),
            system_prompt=system_prompt,
        )

    async def run(self, input_data: GuardrailInput) -> GuardrailOutput:
        """Validate and moderate content.

        Args:
            input_data: GuardrailInput containing response_text and optional product_data

        Returns:
            GuardrailOutput with approved, modified_text, sales_doublecheck, reason_recheck
        """
        # Format product data if provided
        product_text = ""
        if input_data.product_data:
            product_text = "\n\nProduct Data:\n"
            if isinstance(input_data.product_data, list):
                for i, product in enumerate(input_data.product_data, 1):
                    if isinstance(product, dict):
                        product_text += (
                            f"{i}. {json.dumps(product, ensure_ascii=False, indent=2)}\n"
                        )
                    else:
                        product_text += f"{i}. {product}\n"
            else:
                product_text += json.dumps(input_data.product_data, ensure_ascii=False, indent=2)

        # Format input for the agent
        prompt = f"""Validate and moderate this content:

Response Text:
{input_data.response_text}
{product_text}

Check for:
1. Content accuracy and truthfulness
2. Business rules compliance
3. Sales claims accuracy (pricing, availability, features)
4. Professional tone and language
5. Legal compliance (no false claims, misleading statements)
6. Product data consistency (if product_data provided)

Provide validation result with:
- approved: true if content is safe to use (after any modifications)
- modified_text: corrected version if changes needed, null if no changes
- sales_doublecheck: true if sales-related content needs human review
- reason_recheck: explanation if double-check or modification is needed"""

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
            # Fallback: approve with double-check flag
            json_data = {
                "approved": True,
                "modified_text": None,
                "sales_doublecheck": True,
                "reason_recheck": "Unable to parse guardrail response, flagging for review",
            }

        # Ensure required fields are present
        if "approved" not in json_data:
            json_data["approved"] = True  # Default to approved if unclear
        if "modified_text" not in json_data:
            json_data["modified_text"] = None
        # Handle case where modified_text might be empty string
        if json_data.get("modified_text") == "":
            json_data["modified_text"] = None
        if "sales_doublecheck" not in json_data:
            json_data["sales_doublecheck"] = False
        if "reason_recheck" not in json_data:
            json_data["reason_recheck"] = None

        return GuardrailOutput(**json_data)
