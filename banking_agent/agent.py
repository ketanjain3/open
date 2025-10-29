# agent.py

from __future__ import annotations
import os

from google.adk.agents import LlmAgent, SequentialAgent
from google.genai import types

# Import prompts and models from other files in our project
from .models import AgentResponse, IntentGuardrailOutput
from .prompt import (
    CONCIERGE_INSTRUCTIONS,
    INTENT_AGENT_PROMPT,
    prompt_with_handoff_instructions,
)

# It's good practice to get the model name from an environment variable
# to avoid hardcoding it.
MODEL_NAME = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

# --- Tool Definition ---
def get_investment_portfolio(user_id: str):
    """
    Retrieves the investment portfolio for a given user ID.
    Returns mock data with stock symbols, shares, and current value.

    Args:
        user_id: The unique identifier for the user.
    """
    print(f"--- Tool: Fetching portfolio for user_id: {user_id} ---")
    # In a real application, this would fetch data from a database or API.
    # Here, we return a mock portfolio.
    mock_portfolio = {
        "GOOGL": {"shares": 50, "current_value_usd": 8950.50},
        "AAPL": {"shares": 100, "current_value_usd": 19500.00},
        "MSFT": {"shares": 75, "current_value_usd": 25500.75},
        "TSLA": {"shares": 25, "current_value_usd": 4550.00},
    }
    return mock_portfolio


# --- Agent Definitions ---

# 1. Intent Agent: The first agent in the sequence. Its only job is to
#    classify the user's intent and pass it to the next agent via session state.
intent_agent = LlmAgent(
    model=MODEL_NAME,
    name="intent_agent",
    description="Classifies the user's intent.",
    instruction=INTENT_AGENT_PROMPT,
    output_schema=IntentGuardrailOutput,
    output_key="user_intent", # The result will be saved to session state with this key
    generate_content_config=types.GenerateContentConfig(temperature=0.1),
)

# 2. Avery Agent: The second agent in the sequence. It uses the intent
#    from the session state to decide how to respond or which tool to use.
avery_agent = LlmAgent(
    name="avery_agent",
    model=MODEL_NAME,
    description="Friendly conversational AI that assists with user inquiries.",
    instruction=prompt_with_handoff_instructions(CONCIERGE_INSTRUCTIONS),
    output_schema=AgentResponse,
    tools=[get_investment_portfolio], # Make the tool available to this agent
    generate_content_config=types.GenerateContentConfig(temperature=0.1),
)

# 3. Root Agent: A SequentialAgent that orchestrates the workflow by
#    running the sub_agents in the specified order.
root_agent = SequentialAgent(
    name="banking_assistant_agent",
    description="An assistant that first identifies user intent and then acts on it.",
    sub_agents=[intent_agent, avery_agent],
)

# Explicitly ensure `root_agent` is available for import.
__all__ = ["root_agent"]