# agent.py

from __future__ import annotations
import os
import asyncio
from dotenv import load_dotenv

from google.adk.agents import LlmAgent, SequentialAgent
from google.genai import types

# Import prompts and models from other files in our project
from .models import AgentResponse, IntentGuardrailOutput
from .prompt import (
    CONCIERGE_INSTRUCTIONS,
    INTENT_AGENT_PROMPT,
    prompt_with_handoff_instructions,
)

# Import RAG functionality
from .rag.retrieval import search_knowledge
import cognee

# Load environment variables
load_dotenv()

# It's good practice to get the model name from an environment variable
# to avoid hardcoding it.
MODEL_NAME = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

# --- Tool Definition ---

async def search_documents(query: str, limit: int = 5) -> str:
    """
    Search the knowledge base for relevant information about innovation, rankings, and related topics.

    This tool queries the Global Innovation Index database to find information about:
    - Innovation metrics and rankings
    - Country-specific innovation data
    - Technology and research insights
    - Economic and development indicators

    Args:
        query: The search query describing what information you're looking for
        limit: Maximum number of results to return (default: 5)

    Returns:
        A formatted string containing the search results with relevant information
    """
    # Configure cognee
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        os.environ["LLM_API_KEY"] = api_key
        cognee.config.llm_api_key = api_key
        cognee.config.set_llm_api_key(api_key)
        cognee.config.set_llm_provider("openai")
        cognee.config.set_llm_model("gpt-4o-mini")

    # Run the async search function
    results = await search_knowledge(query, limit=limit, search_type="summaries")

    if not results:
        return f"No information found for query: '{query}'"

    # Format results for the agent
    formatted_output = f"Information about '{query}':\n\n"

    for idx, result in enumerate(results, 1):
        # Try different keys to get the text content
        if isinstance(result, dict):
            text = (result.get('text') or
                   result.get('content') or
                   result.get('summary') or
                   str(result))
        else:
            text = str(result)

        # Only add non-empty results
        if text and len(text.strip()) > 0:
            formatted_output += f"{text}\n\n"

    return formatted_output.strip()

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
    description="Friendly conversational AI that assists with user inquiries and can search the innovation knowledge base.",
    instruction=prompt_with_handoff_instructions(CONCIERGE_INSTRUCTIONS),
    output_schema=AgentResponse,
    tools=[search_documents],  # RAG-powered search tool
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