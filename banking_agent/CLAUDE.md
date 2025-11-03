# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a banking/investment assistant agent built using Google's Agent Development Kit (ADK). The agent uses a multi-agent architecture with RAG (Retrieval-Augmented Generation) capabilities powered by Cognee to answer questions about investment research documents and innovation data.

## Architecture

### Multi-Agent Sequential System

The system uses a `SequentialAgent` pattern with two specialized agents:

1. **Intent Agent** (`intent_agent` in agent.py:87-95)
   - First agent in the sequence
   - Classifies user intent into categories: `greet`, `investment_related_question`, `general_question`, `out_of_scope`
   - Uses structured output with `IntentGuardrailOutput` schema
   - Saves classification result to session state with key `user_intent`

2. **Avery Agent** (`avery_agent` in agent.py:99-107)
   - Second agent in the sequence
   - Acts as concierge for JP Morgan's Client Assist platform
   - Accesses intent classification from session state
   - Has access to RAG tool `search_documents` for querying knowledge base
   - Returns structured `AgentResponse` with voice/text fields optimized for audio output

3. **Root Agent** (`root_agent` in agent.py:111-115)
   - `SequentialAgent` that orchestrates the workflow
   - Runs sub-agents in order: intent_agent → avery_agent
   - This is the main export and entry point

### RAG System (rag/ directory)

- **ingest.py**: Document ingestion using Cognee
  - `initialize_cognee()`: Sets up Cognee with OpenAI API key from environment
  - `ingest_pdf()`: Ingests single PDF into knowledge base
  - `ingest_documents()`: Batch ingestion of multiple documents
  - `reset_knowledge_base()`: Clears all ingested data

- **retrieval.py**: Knowledge base querying
  - `search_knowledge()`: Main search function with three search types: "summaries", "chunks", "natural_language"
  - `get_context_for_query()`: Returns formatted context string for prompt augmentation
  - `search_with_filters()`: Advanced filtering on search results

- **Integration**: The `search_documents` tool in agent.py:32-81 wraps the async RAG search function and formats results for the agent

### Key Data Models (models.py)

- `AgentResponse`: Structured output with `voice_str` (max 30 words for audio), `text` (markdown formatted), `send_to_ui` flag, and `follow_up_questions` list
- `IntentGuardrailOutput`: Intent classification with `query`, `intent`, `reasoning`, `confidence`, and `allowed` flag
- `IntentCategory`: Enum with GREET, INVESTMENT_RELATED, GENERAL_QUESTION, OUT_OF_SCOPE

### Prompts (prompt.py)

Contains extensive prompt engineering:
- `INTENT_AGENT_PROMPT`: Detailed intent classification instructions with priority rules
- `CONCIERGE_INSTRUCTIONS`: Comprehensive instructions for Avery agent including audio optimization, markdown formatting guidelines, and conversation protocols
- `prompt_with_handoff_instructions()`: Adds multi-agent handoff instructions to prompts

## Reference-Only Dependencies

### google/ - Google ADK Framework (READ-ONLY)

This directory contains the Google Agent Development Kit source code copied from `.venv` for reference purposes. This allows AI agents to understand the core framework implementation when making technical decisions.

**IMPORTANT**: Do NOT modify any files in the `google/` directory. These are strictly for reference to understand how ADK works internally.

Key modules to reference:
- `google/adk/agents`: Contains `LlmAgent`, `SequentialAgent` implementations
- `google/genai`: Contains Gemini API types and configuration

### rag/cognee/ - Cognee RAG Library (READ-ONLY)

This directory contains the Cognee open-source RAG library source code copied from `.venv` for reference purposes. Consult this when understanding how RAG operations work under the hood.

**IMPORTANT**: Do NOT modify any files in the `rag/cognee/` directory. These are strictly for reference to understand Cognee's implementation.

Key areas to reference:
- `rag/cognee/api`: API functions like `search()`, `add()`, `cognify()`
- `rag/cognee/modules`: Core RAG processing modules
- `rag/cognee/config`: Configuration system for LLM providers and vector stores

## Development Commands

### Running the Agent

The agent uses Google's ADK framework. To run:

```bash
# Ensure you're in the banking_agent directory
cd banking_agent

# Run with ADK CLI (if installed)
adk run agent.py
```

### RAG Document Ingestion

```bash
# Navigate to RAG directory
cd rag

# Run example ingestion script
python example.py

# Or run custom ingestion
python ingest.py
```

### Testing

Evaluation test cases are defined in `test_suite.evalset.json` with expected conversation flows.

## Environment Setup

Required environment variables (in `.env`):
- `OPENAI_API_KEY`: For Cognee RAG embeddings and processing (uses gpt-4o-mini)
- `GEMINI_MODEL`: Optional, defaults to "gemini-2.5-flash" for agent LLM
- `LLM_API_KEY`: Set automatically from OPENAI_API_KEY for Cognee

## Important Implementation Details

### Audio-First Design
- The `voice_str` field in `AgentResponse` is limited to 30 words max
- Responses avoid special characters and complex formatting in voice output
- Text field uses rich markdown formatting for UI display
- `send_to_ui` should be `false` for greetings/simple responses, `true` only when displaying document content

### Response Formatting
- Text responses use hierarchical markdown: `##` for titles, `###` for numbered main points (e.g., "### 1. Market Trends")
- Bullet points under each numbered section for supporting details
- Bold (`**text**`) for key figures, percentages, and important terms
- Clear paragraph breaks for readability

### Session State Flow
- Intent agent saves classification to session state with key `user_intent`
- Avery agent reads this intent to inform its response strategy
- This pattern enables sequential processing without explicit handoffs

### RAG Configuration
- Cognee is configured in agent.py:50-56 on each search (sets API key, provider, and model)
- Default search type is "summaries" for processed, relevant information
- Knowledge base focuses on Global Innovation Index data and investment research

### Multi-Agent Transparency
- System is designed to appear as a single unified assistant
- Agents should never mention transfers or handoffs to users
- The `RECOMMENDED_PROMPT_PREFIX` enforces this unified appearance

## File Structure

```
banking_agent/
├── agent.py              # Main agent definitions and orchestration
├── models.py             # Pydantic schemas for structured outputs
├── prompt.py             # Prompt templates and instructions
├── test_suite.evalset.json  # Test cases
├── rag/                  # RAG module
│   ├── ingest.py        # Document ingestion
│   ├── retrieval.py     # Knowledge base search
│   ├── example.py       # Usage examples
│   ├── README.md        # RAG documentation
│   ├── global-innovation-index.pdf  # Example data
│   └── cognee/          # [READ-ONLY] Cognee source for reference
└── google/              # [READ-ONLY] Google ADK source for reference
```

## Dependencies

Core dependencies (see rag/requirements.txt):
- `cognee>=0.1.0`: RAG knowledge base management
- `python-dotenv>=1.0.0`: Environment variable management
- `pypdf>=3.0.0`, `pymupdf>=1.23.0`: PDF processing
- `openai>=1.0.0`: OpenAI API for embeddings
- Google ADK libraries (installed separately or from vendored google/ directory)
