"""Classify Step Agent - Classifies the current step in the sales graph."""

import os
import json
import re
import google.generativeai as genai
from pydantic_ai import Agent
from pydantic_ai.models.gemini import GeminiModel
from agents.models import ClassifyStepInput, ClassifyStepOutput


class ClassifyStepAgent:
    """Agent that classifies the current step in the sales process based on intent and sales graph."""

    def __init__(self, model_name: str = "gemini-2.5-flash"):
        """Initialize the Classify Step Agent.

        Args:
            model_name: Gemini model name to use
        """
        self.name = "ClassifyStepAgent"
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")

        # Configure google.generativeai with API key
        genai.configure(api_key=api_key)

        system_prompt = """You are a Classify Step Agent specialized in determining the current stage in a sales process based on user intent and the sales graph.

Your task is to:
1. Analyze the cleaned intent text
2. Review the sales graph structure and current node
3. Classify the appropriate current sales node
4. Determine which nodes are allowed as next steps
5. Provide a confidence score and optional reason

Common sales nodes include:
- greeting: Initial greeting and introduction
- need_discovery: Understanding customer needs
- solution_matching: Matching solutions to needs
- price_discussion: Discussing pricing and payment
- objection_handling: Handling customer concerns
- closing: Finalizing the sale

The sales graph defines valid transitions between nodes. You must respect these transitions and only suggest allowed next nodes.

Always respond with a valid JSON object matching this structure:
{{
    "current_sales_node": "need_discovery",
    "allowed_next_nodes": ["solution_matching"],
    "reason": "Customer has expressed specific needs",
    "confidence": 0.93
}}"""

        self.agent = Agent(
            model=GeminiModel(model_name),
            system_prompt=system_prompt,
        )

    async def run(self, input_data: ClassifyStepInput) -> ClassifyStepOutput:
        """Classify the current step in sales process.

        Args:
            input_data: ClassifyStepInput containing clean_intent_text and sales_graph

        Returns:
            ClassifyStepOutput with current_sales_node, allowed_next_nodes, reason, confidence
        """
        # Format sales graph
        nodes_str = ", ".join(input_data.sales_graph.nodes)

        # Format input for the agent
        prompt = f"""Classify the current step in the sales process:

Cleaned Intent: {input_data.clean_intent_text}
Current Sales Node: {input_data.sales_graph.current_node}
Available Nodes: {nodes_str}

Based on the intent, determine:
1. The appropriate current sales node
2. Which nodes are allowed as next steps (must be valid transitions)
3. Provide a confidence score and reason if needed."""

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
            # Fallback: use current node from input
            json_data = {
                "current_sales_node": input_data.sales_graph.current_node,
                "allowed_next_nodes": [],
                "reason": "Failed to parse response, using current node",
                "confidence": 0.5,
            }

        # Ensure required fields are present
        if "current_sales_node" not in json_data:
            json_data["current_sales_node"] = input_data.sales_graph.current_node
        if "allowed_next_nodes" not in json_data:
            json_data["allowed_next_nodes"] = []
        if "reason" not in json_data:
            json_data["reason"] = ""
        if "confidence" not in json_data:
            json_data["confidence"] = 0.5

        return ClassifyStepOutput(**json_data)
