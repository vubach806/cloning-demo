"""Base agent class using PydanticAI."""

import os
import google.generativeai as genai
from pydantic_ai import Agent
from pydantic_ai.models.gemini import GeminiModel


class BaseAgent:
    """Base class for all agents."""

    def __init__(self, name: str, system_prompt: str, model_name: str = "gemini-2.5-flash"):
        """Initialize the agent.

        Args:
            name: Agent name
            system_prompt: System prompt for the agent
            model_name: Gemini model name to use (default: gemini-pro)
                Common models: gemini-pro, gemini-1.5-pro
        """
        self.name = name
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")

        # Configure google.generativeai with API key
        genai.configure(api_key=api_key)

        # GeminiModel reads from environment or uses genai configuration
        self.agent = Agent(
            model=GeminiModel(model_name),
            system_prompt=system_prompt,
        )

    async def run(self, user_input: str) -> str:
        """Run the agent with user input.

        Args:
            user_input: User input message

        Returns:
            Agent response
        """
        result = await self.agent.run(user_input)
        # PydanticAI returns result with data attribute
        return str(result.data) if hasattr(result, "data") else str(result)
