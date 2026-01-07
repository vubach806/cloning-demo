"""Tests for agent functionality."""

import pytest
from agents.coordinator_agent import CoordinatorAgent
from agents.research_agent import ResearchAgent
from agents.analysis_agent import AnalysisAgent


@pytest.mark.asyncio
async def test_coordinator_agent():
    """Test coordinator agent initialization and basic functionality."""
    agent = CoordinatorAgent()
    assert agent.name == "Coordinator"
    # Note: Actual run test would require OpenAI API key
    # result = await agent.run("Hello")
    # assert isinstance(result, str)


@pytest.mark.asyncio
async def test_research_agent():
    """Test research agent initialization."""
    agent = ResearchAgent()
    assert agent.name == "Research"


@pytest.mark.asyncio
async def test_analysis_agent():
    """Test analysis agent initialization."""
    agent = AnalysisAgent()
    assert agent.name == "Analysis"
