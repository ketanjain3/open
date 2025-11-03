# agent.py
"""
Multi-Agent Banking Assistant System

BUSINESS CONTEXT:
This module implements a sequential multi-agent system for JP Morgan's Client Assist platform,
serving US Private Bank Clients. The system provides a conversational AI interface for
navigating investment research documents while maintaining strict compliance and safety standards.

KEY BUSINESS CONSTRAINTS:
1. Voice Response Limit: 30-word maximum for audio delivery system integration
2. No Investment Advice: Legal/compliance requirement - information only, never personalized recommendations
3. Unified System Appearance: Multi-agent architecture must be invisible to users
4. RAG-Grounded Responses: Agent must NEVER hallucinate - all responses grounded in document content
5. Deterministic Behavior: Temperature 0.1 for consistency, compliance testing, and risk mitigation
6. Accessibility: Dual output format (voice + rich text) for voice UI and visual displays

ARCHITECTURE:
Sequential workflow with two specialized agents:
  1. Intent Agent: Safety/compliance gate that classifies user intent before processing
  2. Avery Agent: Main conversational agent with RAG-powered document search capabilities

Agents communicate via session state (output_key mechanism) to create seamless user experience
while maintaining clean separation of concerns.

TARGET AUDIENCE: US Private Bank Clients
DOMAIN: Banking & Investment Research Navigation
"""

from __future__ import annotations
import os
import asyncio
from dotenv import load_dotenv

# Google ADK Framework - Multi-agent orchestration and LLM integration
from google.adk.agents import LlmAgent, SequentialAgent, LoopAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.tools import ToolContext
from google.genai import types
from typing import Optional
import logging
import json

# Structured data models - Ensures type safety, validation, and consistent output format
# BUSINESS REASON: Pydantic models provide schema validation for compliance/audit requirements
from .models import AgentResponse, IntentGuardrailOutput, ValidationResult

# Agent instructions - Separated for maintainability and prompt engineering iteration
# BUSINESS REASON: Prompts contain critical business rules, constraints, and compliance requirements
from .prompt import (
    CONCIERGE_INSTRUCTIONS,          # Main agent behavior and response formatting rules
    INTENT_AGENT_PROMPT,              # Intent classification logic and safety guardrails
    VALIDATOR_INSTRUCTIONS,           # Validation agent instructions for response quality checks
    prompt_with_handoff_instructions,  # Ensures unified system appearance (hides multi-agent architecture)
)

# RAG (Retrieval-Augmented Generation) functionality using Cognee
# BUSINESS REASON: Compliance/accuracy requirement - prevents hallucination, ensures responses
# are grounded in actual document content (Global Innovation Index database)
from .rag.retrieval import search_knowledge
import cognee

# Environment configuration
load_dotenv()

# Logging configuration for validation failures and compliance monitoring
logger = logging.getLogger(__name__)

# Model configuration from environment variable for deployment flexibility
# BUSINESS DECISION: gemini-2.5-flash chosen as default for performance/cost balance
# Different environments (dev/staging/prod) can use different models without code changes
MODEL_NAME = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

# ============================================================================
# RAG TOOL: search_documents
# ============================================================================
# BUSINESS REQUIREMENTS:
# 1. Data Source Priority: Must check knowledge base before providing information
# 2. Compliance/Accuracy: Prevent hallucination by requiring grounded responses
# 3. Recency Requirements: Ensure responses use latest regulatory/market information
# 4. Ground Truth Constraint: Agent outputs (voice, text, follow_ups) must ALL
#    be derived from RAG tool output - NEVER use pre-trained knowledge
#
# CRITICAL CONSTRAINT:
# The agent must NOT generate information not present in search results. This includes:
# - Voice responses must only reference retrieved content
# - Text responses must only cite retrieved documents
# - Follow-up questions must only cover topics the RAG tool can handle
# - No hallucination or speculation beyond document content
#
# FUTURE EXTENSIBILITY:
# Currently single tool (search_documents), but architecture supports adding:
# - Document comparison tools
# - Metadata query tools
# - Multi-document aggregation tools
# ============================================================================

async def search_documents(
    query: str,
    limit: int = 5,
    tool_context: ToolContext = None
) -> str:
    """
    Search the knowledge base for relevant information about innovation, rankings, and related topics.

    This tool queries the Global Innovation Index database to find information about:
    - Innovation metrics and rankings
    - Country-specific innovation data
    - Technology and research insights
    - Economic and development indicators

    BUSINESS CONSTRAINTS:
    - All agent responses MUST be grounded in results from this tool
    - No fabrication or hallucination allowed
    - If no results found, agent must explicitly state this and escalate
    - Document citations required for all factual claims

    VALIDATION INTEGRATION:
    - Tool output is stored in temp:last_rag_output for validation agent access
    - Temp state persists across loop iterations within same invocation
    - Automatically cleared between user messages

    Args:
        query: The search query describing what information you're looking for
        limit: Maximum number of results to return (default: 5)
        tool_context: Tool context for state management (provided by ADK framework)

    Returns:
        A formatted string containing the search results with relevant information
    """
    # Configure Cognee RAG system
    # BUSINESS DECISION: OpenAI used for embeddings/RAG processing (separate from Gemini agent LLM)
    # REASON: OpenAI embeddings proven reliable for financial document retrieval
    # MODEL: gpt-4o-mini chosen for cost-effective embedding generation
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        os.environ["LLM_API_KEY"] = api_key
        cognee.config.llm_api_key = api_key
        cognee.config.set_llm_api_key(api_key)
        cognee.config.set_llm_provider("openai")
        cognee.config.set_llm_model("gpt-4o-mini")

    # Execute RAG search
    # SEARCH_TYPE: "summaries" chosen for processed, relevant information vs raw chunks
    # BUSINESS REASON: Summaries provide better context for agent to generate concise responses
    results = await search_knowledge(query, limit=limit, search_type="summaries")

    # Handle no results case - CRITICAL for compliance
    # Agent MUST explicitly state when information is not available (no fabrication allowed)
    if not results:
        formatted_output = f"No information found for query: '{query}'"

        # Store in temp state for validator access
        if tool_context:
            tool_context.state["temp:last_rag_output"] = formatted_output
            tool_context.state["temp:rag_query"] = query
            # Initialize retry counter if first call
            if "temp:retry_count" not in tool_context.state:
                tool_context.state["temp:retry_count"] = 0

        return formatted_output

    # Format results for agent consumption
    # BUSINESS REQUIREMENT: Clear, structured format enables accurate citation and response generation
    formatted_output = f"Information about '{query}':\n\n"

    for idx, result in enumerate(results, 1):
        # Flexible key handling for different Cognee result formats
        # FUTURE EXTENSIBILITY: Supports different search_type outputs (summaries, chunks, natural_language)
        if isinstance(result, dict):
            text = (result.get('text') or
                   result.get('content') or
                   result.get('summary') or
                   str(result))
        else:
            text = str(result)

        # Quality filter: Only include non-empty results
        # BUSINESS REASON: Prevents agent from processing empty/null content
        if text and len(text.strip()) > 0:
            formatted_output += f"{text}\n\n"

    formatted_output = formatted_output.strip()

    # Store formatted output in temp state for validator agent access
    # VALIDATION INTEGRATION:
    # - temp: prefix ensures state is cleared between user messages
    # - Persists across loop iterations within same invocation
    # - Validator agent reads this to check response grounding
    if tool_context:
        tool_context.state["temp:last_rag_output"] = formatted_output
        tool_context.state["temp:rag_query"] = query

        # Initialize all template variables to prevent KeyError
        # ADK substitutes template variables before evaluating conditionals
        if "temp:retry_count" not in tool_context.state:
            tool_context.state["temp:retry_count"] = 0
        if "temp:validation_feedback" not in tool_context.state:
            tool_context.state["temp:validation_feedback"] = ""
        if "temp:is_valid" not in tool_context.state:
            tool_context.state["temp:is_valid"] = False

    return formatted_output

# ============================================================================
# AGENT 1: INTENT CLASSIFICATION AGENT
# ============================================================================
# BUSINESS PURPOSE: Safety and compliance gate before main processing
#
# WHY THIS AGENT EXISTS:
# - User Safety: Filters inappropriate requests (out-of-scope, illegal activities)
# - Compliance: Logs and tracks user intent categories for audit requirements
# - Routing Logic: Enables future conditional processing based on intent type
# - Risk Mitigation: Prevents sensitive/illegal queries from reaching main agent
#
# INTENT CATEGORIES (4 types):
# 1. greet: Simple standalone greetings ONLY (no other content)
# 2. investment_related_question: Questions about GIS, KIT, TMT, EOTM, care chooses,
#    MM, LTCMA, outlook, document metadata (expiration dates, activity status, LOB, region)
# 3. general_question: Agent identity, capabilities, limitations, conversational exchanges
# 4. out_of_scope: Outside banking/investment domain, illegal activities, personal topics
#
# PRIORITY RULES FOR MIXED-INTENT MESSAGES:
# - Agent-related questions → general_question (even if greeting present)
# - Investment-related content → investment_related_question (when combined with other elements)
# - Pure simple greeting → greet
# - Outside allowed scope → out_of_scope (allowed=false)
#
# OUTPUT SCHEMA: IntentGuardrailOutput
# - query: Original user message (audit trail)
# - intent: IntentCategory enum (routing logic)
# - reasoning: Detailed explanation (transparency, debugging, QA)
# - confidence_float: 0.0-1.0 (flag low-confidence classifications for review)
# - allowed: Boolean (security gate - false ONLY for out_of_scope)
#
# SESSION STATE COMMUNICATION:
# - Uses output_key="user_intent" to save classification to session state
# - Avery agent reads this value to inform response strategy
# - Enables clean agent separation without explicit handoffs
# ============================================================================
intent_agent = LlmAgent(
    model=MODEL_NAME,
    name="intent_agent",
    description="Classifies the user's intent.",
    instruction=INTENT_AGENT_PROMPT,  # See prompt.py for detailed classification rules
    output_schema=IntentGuardrailOutput,  # Structured output for validation and audit
    output_key="user_intent",  # Save to session state for downstream agent consumption

    # TEMPERATURE: 0.1 for deterministic intent classification
    # BUSINESS REASONS:
    # - Consistency/Determinism: Same query should always get same intent classification
    # - Compliance Testing: Evaluation and audit processes need reproducible behavior
    # - Risk Mitigation: Minimize unpredictable classifications in regulated domain
    # - Brand Voice Consistency: Maintain consistent intent detection across interactions
    generate_content_config=types.GenerateContentConfig(temperature=0.1),
)

# ============================================================================
# CALLBACK: Initialize Template Variables
# ============================================================================
# BUSINESS PURPOSE: Ensure all template variables exist in state before
# concierge and validator agents process their instructions
#
# WHY THIS IS NEEDED:
# - ADK substitutes template variables ({{var}}) before evaluating conditionals
# - Variables must exist even if inside {% if %} blocks
# - Greetings don't call search_documents(), so variables wouldn't be initialized
# - Prevents KeyError when processing CONCIERGE_INSTRUCTIONS and VALIDATOR_INSTRUCTIONS
#
# INITIALIZED VARIABLES:
# - temp:retry_count: Tracks retry iteration (0 on first attempt)
# - temp:validation_feedback: Stores validator feedback for retry
# - temp:is_valid: Stores final validation result
# - temp:last_rag_output: RAG tool output for validator (empty if tool not called)
# - temp:rag_query: Original RAG query for debugging (empty if tool not called)
# ============================================================================
async def initialize_temp_state(callback_context: CallbackContext) -> None:
    """
    Initialize temp state variables before concierge agent runs.

    Ensures all template variables referenced in CONCIERGE_INSTRUCTIONS and
    VALIDATOR_INSTRUCTIONS exist, preventing KeyError during template substitution.

    This is critical for greetings and other responses where search_documents()
    is not called, so RAG-related variables wouldn't be initialized by the tool.

    Args:
        callback_context: Callback context with access to session state
    """
    # Initialize temp state variables if they don't exist
    # These are used in template variables in CONCIERGE_INSTRUCTIONS and VALIDATOR_INSTRUCTIONS
    if "temp:retry_count" not in callback_context.state:
        callback_context.state["temp:retry_count"] = 0
    if "temp:validation_feedback" not in callback_context.state:
        callback_context.state["temp:validation_feedback"] = ""
    if "temp:is_valid" not in callback_context.state:
        callback_context.state["temp:is_valid"] = False
    if "temp:last_rag_output" not in callback_context.state:
        # Initialize to empty string - will be populated by search_documents() if called
        # For greetings/non-RAG responses, validator should handle empty RAG output appropriately
        callback_context.state["temp:last_rag_output"] = ""
    if "temp:rag_query" not in callback_context.state:
        callback_context.state["temp:rag_query"] = ""

    # Return None to proceed with normal agent execution
    return None


# ============================================================================
# AGENT 2: CONCIERGE (MAIN CONVERSATIONAL AGENT)
# ============================================================================
# BUSINESS PURPOSE: Professional concierge for JP Morgan's Client Assist platform
# serving US Private Bank Clients (known to users as "Avery")
#
# IDENTITY CONSTRAINTS:
# - Name: "Avery" (user-facing identity)
# - Organization: "JP Morgan's Client Assist platform"
# - Target Audience: "US Private Bank Clients"
# - Role: Professional concierge for investment content navigation
# - Tone: Professional yet conversational, optimized for audio delivery
#
# CRITICAL BUSINESS CONSTRAINTS:
#
# 1. VOICE/TEXT DUAL-OUTPUT FORMAT:
#    Why: Voice UI integration + Accessibility requirements
#    - voice_str: 30-word MAXIMUM (hard limit for audio delivery system)
#      * Natural conversational language for text-to-speech
#      * NO special characters, symbols, or complex formatting
#      * Simple spoken language that flows naturally when read aloud
#    - text: Rich markdown formatting for visual UI display
#      * Hierarchical structure: ## for titles, ### for numbered points
#      * Bullet points under each numbered section
#      * **bold** for key figures, percentages, statistics
#    - send_to_ui: Boolean gating logic
#      * false: Greetings, simple responses WITHOUT document content
#      * true: ONLY when text contains substantial markdown document information
#      * Purpose: Prevent UI clutter for simple conversational exchanges
#    - follow_up_questions: List of 1-3 contextual follow-up questions
#      * ONLY in follow_up_questions array - NEVER in voice/text fields
#      * Phrased as direct statements (not "would you like" format)
#      * Short, concise, action-oriented, naturally conversational
#      * Must be directly related to documents and previous discussion
#      * OPTIONAL: Include when naturally extends conversation, skip when forced
#
# 2. NO INVESTMENT ADVICE:
#    Why: Legal/compliance requirement
#    - Information sharing ONLY, never personalized recommendations
#    - Clear boundaries between information and advice
#    - Escalate complex financial planning to human advisors
#    - Escalation protocols defined in prompt.py
#
# 3. RAG-GROUNDED RESPONSES (CRITICAL):
#    Why: Data source priority, Compliance/accuracy, Recency requirements
#    - ALL responses must be grounded in search_documents tool output
#    - NEVER hallucinate or use pre-trained knowledge beyond documents
#    - Voice responses: Only reference retrieved content
#    - Text responses: Only cite retrieved documents
#    - Follow-up questions: Only cover topics RAG tool can handle
#    - If no results found: Explicitly state and escalate (see prompt.py)
#    - Document citations REQUIRED for all factual claims
#    - VALIDATION: Responses validated by validator_agent for grounding and consistency
#
# 4. TEMPERATURE 0.1:
#    Why: Consistency/determinism, Compliance testing, Risk mitigation, Brand voice
#    - Banking/investment domain requires predictable, consistent responses
#    - Enables reproducible behavior for evaluation and audit
#    - Minimizes creative/unexpected responses in regulated domain
#
# 5. UNIFIED SYSTEM APPEARANCE:
#    Why: UX requirement - hide multi-agent complexity from users
#    - NEVER mention transferring to another agent or specialist
#    - NEVER introduce as specific agent type
#    - Present entire system as ONE unified assistant
#    - prompt_with_handoff_instructions() enforces this (see prompt.py)
#
# TOOLS:
# - search_documents: RAG-powered knowledge base search (only tool currently)
#   FUTURE EXTENSIBILITY: Architecture supports adding more tools:
#   - Document comparison tools
#   - Metadata query tools
#   - Multi-document aggregation tools
#
# OUTPUT SCHEMA: AgentResponse
# - voice_str: ≤30 words, audio-optimized (BUSINESS: audio delivery constraint)
# - text: Markdown formatted, hierarchical (BUSINESS: rich visual display)
# - send_to_ui: Boolean gate (BUSINESS: prevent UI clutter)
# - follow_up_questions: List[str] (BUSINESS: optional conversation deepening)
#
# SESSION STATE:
# - INPUT: Reads "user_intent" from session state (set by intent_agent)
# - OUTPUT: Saves response to "avery_response" via output_key (for validator_agent)
# - VALIDATION FEEDBACK: Reads "temp:validation_feedback" on retry attempts
# ============================================================================
avery_agent = LlmAgent(
    name="avery_agent",
    model=MODEL_NAME,
    description="Friendly conversational AI that assists with user inquiries and can search the innovation knowledge base.",

    # Instruction includes handoff instructions to ensure unified system appearance
    # VALIDATION: Also includes retry feedback template that reads temp:validation_feedback
    # See prompt.py for comprehensive business rules, constraints, and formatting guidelines
    instruction=prompt_with_handoff_instructions(CONCIERGE_INSTRUCTIONS),

    output_schema=AgentResponse,  # Structured output enforces voice/text separation and formatting

    # OUTPUT KEY: Auto-saves response to session state for validator agent access
    # VALIDATION INTEGRATION: Validator reads this to check grounding and consistency
    output_key="avery_response",

    # RAG-powered search tool - ONLY tool currently
    # FUTURE EXTENSIBILITY: Can add document comparison, metadata query, aggregation tools
    # VALIDATION: Tool stores output in temp:last_rag_output for validation
    tools=[search_documents],

    # TEMPERATURE: 0.1 for consistent, deterministic responses
    # Same business rationale as intent_agent (consistency, compliance, risk mitigation)
    generate_content_config=types.GenerateContentConfig(temperature=0.1),

    # CALLBACK: Initialize temp state variables before agent runs
    # CRITICAL: Ensures template variables exist even when search_documents() isn't called
    # (e.g., for greetings) - prevents KeyError during instruction template substitution
    before_agent_callback=initialize_temp_state,
)

# ============================================================================
# AGENT 3: VALIDATOR (RESPONSE QUALITY VALIDATION AGENT)
# ============================================================================
# BUSINESS PURPOSE: Ensure responses meet strict compliance and quality requirements
# before being shown to users
#
# WHY THIS AGENT EXISTS:
# - Compliance: Enforces RAG-grounded responses (no hallucination/fabrication)
# - Quality Assurance: Validates voice/text semantic consistency
# - Risk Mitigation: Catches violations before reaching users
# - Audit Trail: Provides specific feedback for failed validations
#
# VALIDATION CHECKS (2 CRITICAL REQUIREMENTS):
#
# 1. Tool Output Traceability (CRITICAL):
#    - ALL claims in voice_str must be present in RAG tool output
#    - ALL claims in text field must be present in RAG tool output
#    - NO fabrication from pre-trained knowledge
#    - NO inference beyond RAG results
#
# 2. Voice/Text Semantic Consistency:
#    - voice_str and text must convey SAME core information
#    - text should elaborate/expand on voice, not different facts
#    - NO contradictions between fields
#
# OUTPUT SCHEMA: ValidationResult
# - is_valid: Boolean (final verdict)
# - traceability_check: Boolean (RAG grounding check)
# - consistency_check: Boolean (voice/text alignment check)
# - feedback: Specific, actionable feedback for retry (empty if valid)
# - escalate: Boolean flag to control LoopAgent (true=exit, false=retry)
#
# SESSION STATE:
# - INPUT: Reads "avery_response" (concierge output) and "temp:last_rag_output"
# - OUTPUT: Stores "temp:validation_feedback" for next retry attempt
# - LOOP CONTROL: Sets escalate=True to exit loop, False to continue retry
#
# INTEGRATION WITH RETRY LOOP:
# - Runs after avery_agent in each LoopAgent iteration
# - If invalid: Stores feedback in temp state, returns escalate=False
# - If valid: Returns escalate=True to exit loop
# - Max 3 iterations before fallback
# ============================================================================
validator_agent = LlmAgent(
    name="validator_agent",
    model=MODEL_NAME,
    description="Response quality validator ensuring compliance with grounding and consistency requirements.",

    # VALIDATOR INSTRUCTIONS: Uses template variables to read response + RAG output from state
    # See prompt.py for detailed validation criteria, examples, and feedback guidelines
    instruction=VALIDATOR_INSTRUCTIONS,

    output_schema=ValidationResult,  # Structured validation result with specific feedback

    # TEMPERATURE: 0.2 for nuanced validation judgment
    # REASON: Slightly higher than concierge (0.1) to allow flexibility in validation decisions
    # while maintaining consistency
    generate_content_config=types.GenerateContentConfig(temperature=0.2),
)

# ============================================================================
# FALLBACK HANDLER: Validation Failure After Max Retries
# ============================================================================
# BUSINESS PURPOSE: Provide safe escalation when validation fails after 3 attempts
#
# COMPLIANCE REQUIREMENT:
# - Log failures for audit/review
# - Return professional escalation message
# - Maintain user experience (no error messages)
#
# TRIGGERED WHEN:
# - Validation fails after max_iterations (3 attempts)
# - temp:is_valid still False after loop exits
# ============================================================================
async def handle_validation_failure(callback_context: CallbackContext) -> Optional[types.Content]:
    """
    Handle case where validation fails after max retry attempts.
    Returns safe fallback message to user.

    BUSINESS REQUIREMENTS:
    - Log failure for compliance review
    - Return professional escalation message (not error)
    - Maintain consistent AgentResponse format

    Args:
        callback_context: Callback context with access to session state

    Returns:
        Safe fallback Content if validation failed, None if validation passed
    """
    # Check if validation passed
    # ValidationResult stores is_valid in temp state via validator agent
    is_valid = callback_context.state.get("temp:is_valid", False)
    retry_count = callback_context.state.get("temp:retry_count", 0)

    # If validation passed or no retries occurred, allow normal response
    if is_valid or retry_count == 0:
        return None

    # Log failure for compliance review
    # AUDIT REQUIREMENT: Track all validation failures for quality assurance
    validation_feedback = callback_context.state.get("temp:validation_feedback", "Unknown issue")
    logger.error(
        f"Validation failed after {retry_count} attempts. "
        f"Last feedback: {validation_feedback}"
    )

    # Return safe fallback message
    # BUSINESS REQUIREMENT: Professional escalation, not technical error
    fallback_response = AgentResponse(
        voice_str="I need to connect you with a specialist for this question.",
        text="I apologize, but I need to escalate your question to ensure you receive accurate information. A specialist will assist you shortly.",
        send_to_ui=True,
        follow_up_questions=[]
    )

    # Return as Content for ADK framework
    return types.Content(parts=[
        types.Part(text=fallback_response.model_dump_json())
    ])

# ============================================================================
# LOOP AGENT: CONCIERGE WITH VALIDATION RETRY
# ============================================================================
# BUSINESS PURPOSE: Wrap concierge + validator in retry loop for quality assurance
#
# WHY LOOP PATTERN:
# - Self-Correction: Agent gets feedback and can improve response
# - Quality Gate: Validation ensures compliance before user sees response
# - Graceful Degradation: Fallback after max retries maintains user experience
#
# WORKFLOW (Max 3 Iterations):
# 1. avery_agent executes:
#    - Reads temp:validation_feedback if retry_count > 0
#    - Calls search_documents (stores temp:last_rag_output)
#    - Generates AgentResponse (stored as avery_response)
#
# 2. validator_agent executes:
#    - Reads avery_response and temp:last_rag_output from state
#    - Validates traceability + consistency
#    - If invalid: Stores temp:validation_feedback, returns escalate=False → loop continues
#    - If valid: Returns escalate=True → loop exits
#
# 3. If max_iterations reached without valid response:
#    - handle_validation_failure callback triggers
#    - Returns safe escalation message
#
# EXIT CONDITIONS:
# - Success: validator_agent returns escalate=True
# - Max Retries: Reached 3 iterations → fallback handler
# ============================================================================
avery_with_validation = LoopAgent(
    name="avery_with_validation",
    sub_agents=[avery_agent, validator_agent],
    max_iterations=3,  # Maximum retry attempts before fallback
)

# Attach fallback handler for max retries scenario
# COMPLIANCE: Ensures professional escalation on persistent validation failure
avery_with_validation.after_agent_callback = handle_validation_failure

# ============================================================================
# ROOT AGENT: SEQUENTIAL ORCHESTRATOR
# ============================================================================
# BUSINESS PURPOSE: Orchestrates multi-agent workflow while maintaining
# unified system appearance to users
#
# ARCHITECTURE PATTERN: SequentialAgent with nested LoopAgent
# Why this pattern:
# - Clean separation of concerns (intent classification → validated processing)
# - Safety gate: Intent agent filters inappropriate requests before main agent
# - Quality gate: Validation ensures RAG-grounded, consistent responses
# - Extensibility: Easy to add more agents in the sequence as needed
# - Session state communication: Agents share data without explicit coupling
#
# WORKFLOW:
# 1. intent_agent: Classifies user message, saves to session state as "user_intent"
# 2. avery_with_validation (LoopAgent, max 3 iterations):
#    a. avery_agent: Reads intent, processes request with RAG, generates response
#    b. validator_agent: Validates grounding and consistency
#    c. If invalid: Loop continues with feedback
#    d. If valid: Loop exits
#    e. If max retries: Fallback handler returns escalation message
#
# BUSINESS CONSTRAINTS:
# 1. UNIFIED SYSTEM APPEARANCE (CRITICAL):
#    - Users must NEVER know multiple agents are involved
#    - No visible handoffs or transitions between agents
#    - Entire system presents as single "Avery" assistant
#    - prompt_with_handoff_instructions() ensures this transparency
#    - Validation loop is completely transparent to users
#
# 2. SEQUENTIAL PROCESSING:
#    - Intent classification MUST complete before main processing
#    - Safety/compliance gate enforced by sequential execution
#    - Enables future conditional routing based on intent
#
# 3. VALIDATION LOOP (NEW):
#    - Quality gate enforces RAG-grounded responses
#    - Self-correction via retry with feedback
#    - Graceful degradation via fallback after max retries
#    - Compliance requirement for regulated banking domain
#
# 4. SESSION STATE COMMUNICATION:
#    - Agents communicate via session state keys (output_key mechanism)
#    - Clean decoupling: No direct agent-to-agent dependencies
#    - Pattern supports adding more agents without refactoring
#
# FUTURE EXTENSIBILITY:
# Design supports adding specialized agents to the sequence:
# - Document comparison agent (for multi-document analysis)
# - Escalation agent (for complex queries requiring human advisors)
# - Analytics agent (for tracking conversation quality/metrics)
# - Personalization agent (for client-specific customization)
#
# INTEGRATION PATTERNS:
# This root_agent is the main entry point and can be used via:
# - ADK CLI: `adk run banking_agent` (interactive testing)
# - ADK Web UI: `adk web .` (visual interface)
# - Programmatic: Import and use with ADK session management
# ============================================================================
root_agent = SequentialAgent(
    name="banking_assistant_agent",
    description="An assistant that first identifies user intent, then processes it with validation.",

    # Sequential execution order: intent_agent → avery_with_validation (LoopAgent)
    # BUSINESS REQUIREMENT: Intent classification, then validated response generation
    sub_agents=[intent_agent, avery_with_validation],
)

# ============================================================================
# MODULE EXPORTS
# ============================================================================
# root_agent is the main entry point for the banking assistant system
# Import pattern: from banking_agent.agent import root_agent
# ============================================================================
__all__ = ["root_agent"]