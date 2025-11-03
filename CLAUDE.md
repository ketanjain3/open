# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository contains learning experiments with Google's Agents Development Kit (ADK), focusing on building conversational AI agents with RAG capabilities. The main implementations are:

1. **Banking Agent** (`banking_agent/`) - A multi-agent system with intent classification and RAG-powered knowledge retrieval
2. **Tool Callback Agent** (`tool_callback_agent/`) - A basic agent demonstration (minimal implementation)

### Reference-Only Directories

**IMPORTANT**: The following directories are copied from `.venv/` for reference purposes only. They help AI assistants understand the framework internals. **DO NOT modify these directories**:

- `banking_agent/google/` - Google ADK package and dependencies (Agent Development Kit framework)
- `banking_agent/rag/cognee/` - Cognee RAG library source code

These are included to provide context about how the underlying frameworks work when making technical decisions.

## Technology Stack

- **Agent Framework**: Google Agents Development Kit (ADK) - `google.adk.agents`
- **LLM Provider**: Google Gemini (default: `gemini-2.5-flash`)
- **RAG System**: [Cognee](https://github.com/topoteretes/cognee) - Knowledge graph-based RAG
- **Document Processing**: PyPDF, PyMuPDF for PDF ingestion
- **Embeddings**: OpenAI (configurable via Cognee)

## Environment Setup

### Required Environment Variables

Create `.env` files in agent directories with:
```bash
# For Gemini models
GEMINI_MODEL=gemini-2.5-flash  # or other Gemini model
GOOGLE_API_KEY=your-api-key

# For RAG (OpenAI embeddings)
OPENAI_API_KEY=your-openai-key
LLM_API_KEY=your-openai-key  # Used by Cognee
```

### Python Environment

This project uses a virtual environment at `.venv/`. Activate it with:

```bash
source .venv/bin/activate
```

### Installing Dependencies

Install RAG dependencies:
```bash
pip install -r banking_agent/rag/requirements.txt
```

Core dependencies include:
- `cognee>=0.1.0` - RAG framework
- `python-dotenv>=1.0.0` - Environment variables
- `pypdf>=3.0.0`, `pymupdf>=1.23.0` - PDF processing
- `openai>=1.0.0` - OpenAI embeddings (default for Cognee)

The Google ADK is also required but is included in the `.venv/`.

## Common Development Commands

### Running the Banking Agent

Run the agent interactively using the ADK CLI:

```bash
# From the project root
adk run banking_agent

# Save session on exit
adk run banking_agent --save_session

# Resume from saved session
adk run banking_agent --resume session.json
```

### Running with Web UI

Start the web interface for interactive testing:

```bash
# From the project root
adk web .

# With custom port
adk web . --port 8080

# With auto-reload enabled
adk web . --reload
```

Access the UI at `http://127.0.0.1:8000` (or your specified port).

### Running Evaluations

Evaluate the agent against test cases:

```bash
# Run all test cases from the eval set
adk eval banking_agent banking_agent/test_suite.evalset.json

# Run specific test cases only
adk eval banking_agent banking_agent/test_suite.evalset.json:test_case_1,test_case_2

# Print detailed results
adk eval banking_agent banking_agent/test_suite.evalset.json --print_detailed_results
```

Evaluation results are stored in `banking_agent/.adk/eval_history/`.

### Running RAG Examples

Test RAG ingestion and retrieval:

```bash
cd banking_agent/rag
python example.py
```

This will:
1. Initialize Cognee
2. Ingest the example PDF
3. Run sample queries
4. Display results

## Architecture

### Banking Agent - Multi-Agent Sequential System with Validation Loop

The banking agent (`banking_agent/agent.py`) uses a **SequentialAgent** pattern with nested **LoopAgent** for quality validation:

1. **Intent Agent** (`intent_agent`)
   - Purpose: Classifies user messages into intent categories
   - Output: Structured `IntentGuardrailOutput` saved to session state as `user_intent`
   - Categories: `greet`, `investment_related_question`, `general_question`, `out_of_scope`
   - Temperature: 0.1 for consistent classification

2. **Concierge with Validation** (`concierge_with_validation` - LoopAgent, max 3 iterations)
   - **Concierge Agent** (formerly `avery_agent`)
     - Purpose: Main conversational agent that handles user queries
     - Reads intent from session state (`user_intent` key)
     - Has access to RAG tool: `search_documents(query, limit, tool_context)`
     - Output: Structured `AgentResponse` saved as `avery_response`
     - Temperature: 0.1
     - Reads `temp:validation_feedback` on retry attempts for self-correction

   - **Validator Agent** (quality gate)
     - Purpose: Ensures RAG-grounded responses and voice/text consistency
     - Validates: Tool output traceability + semantic consistency
     - Output: `ValidationResult` with specific feedback
     - Temperature: 0.2
     - Returns `escalate=True` to exit loop, `False` to retry

   - **Fallback Handler**: Returns professional escalation message after max retries

3. **Root Agent** (`root_agent`)
   - Type: `SequentialAgent` that orchestrates the workflow
   - Runs sub-agents: intent_agent → concierge_with_validation (LoopAgent)
   - Entry point for the system

### Key Design Patterns

**Session State Communication**: Agents communicate via session state using the `output_key` parameter. The intent agent saves its classification as `user_intent`, which the avery agent consumes.

**Structured Outputs**: Both agents use Pydantic models (`IntentGuardrailOutput`, `AgentResponse`) for type-safe, validated responses.

**Handoff Instructions**: The system uses `prompt_with_handoff_instructions()` to add multi-agent coordination context to prompts, ensuring seamless handoffs appear as a unified system.

**Voice + Text Response Format**: The `AgentResponse` model separates:
- `voice_str`: Concise (≤30 words) spoken response
- `text`: Rich markdown-formatted content for UI display
- `send_to_ui`: Boolean flag for conditional UI rendering
- `follow_up_questions`: Array of contextual follow-ups

### RAG Module (`banking_agent/rag/`)

The RAG system uses Cognee for document ingestion and retrieval:

**Ingestion** (`ingest.py`):
- `initialize_cognee()` - Configure Cognee with API keys and LLM settings
- `ingest_pdf(pdf_path)` - Ingest single PDF
- `ingest_documents(paths, file_types)` - Batch ingestion from files/directories
- `reset_knowledge_base()` - Clear all ingested data

**Retrieval** (`retrieval.py`):
- `search_knowledge(query, limit, search_type)` - Query knowledge base
  - Search types: `"summaries"`, `"chunks"`, `"natural_language"`
- `get_context_for_query(query, max_tokens)` - Get formatted context for prompts
- `search_with_filters(query, filters, limit)` - Advanced filtered search

**Tool Integration**: The `search_documents()` async function in `agent.py` wraps the RAG retrieval and formats results for the agent.

### Important Files

**Modifiable Agent Files**:
- `banking_agent/agent.py` - Main agent definitions and RAG tool
- `banking_agent/prompt.py` - Agent instruction prompts (`INTENT_AGENT_PROMPT`, `CONCIERGE_INSTRUCTIONS`)
- `banking_agent/models.py` - Pydantic response schemas
- `banking_agent/test_suite.evalset.json` - Test cases for agent evaluation
- `banking_agent/rag/ingest.py` - RAG document ingestion functions
- `banking_agent/rag/retrieval.py` - RAG search and retrieval functions
- `banking_agent/rag/example.py` - Example RAG usage script

**Reference-Only Directories** (DO NOT modify):
- `banking_agent/google/` - Google ADK framework source
- `banking_agent/rag/cognee/` - Cognee RAG library source

**Auto-Generated Directories**:
- `banking_agent/.adk/eval_history/` - Evaluation run results

## Working with the Codebase

### Testing RAG Functionality Programmatically

Import and use RAG functions in Python:

```python
from banking_agent.rag import initialize_cognee, ingest_pdf, search_knowledge

# Initialize
await initialize_cognee()

# Ingest documents
await ingest_pdf("path/to/document.pdf")

# Search
results = await search_knowledge("your query", limit=5)
```

Or run the example script: `cd banking_agent/rag && python example.py`

### Working with Evaluation Sets

Evaluation data is stored in `banking_agent/test_suite.evalset.json`. This JSON file contains test conversations with expected responses for validation. You can:

1. Run all evals: `adk eval banking_agent banking_agent/test_suite.evalset.json`
2. Run specific evals: `adk eval banking_agent banking_agent/test_suite.evalset.json:test_case_1`
3. View results in: `banking_agent/.adk/eval_history/`

### Agent Execution Patterns

Agents can be run in multiple ways:

1. **Interactive CLI**: `adk run banking_agent` (best for development)
2. **Web UI**: `adk web .` (best for demos and testing)
3. **Programmatic**: Import `root_agent` from `banking_agent.agent` and use with ADK's session management

## Code Modification Guidelines

### Adding New Agent Tools

Tools must be async functions with clear docstrings:

```python
async def your_tool(param: str) -> str:
    """
    Clear description of what this tool does.

    Args:
        param: Description of parameter

    Returns:
        Description of return value
    """
    # Implementation
    return result
```

Add to agent's `tools` parameter:
```python
avery_agent = LlmAgent(
    tools=[search_documents, your_tool],
    ...
)
```

### Modifying Agent Instructions

Agent prompts are defined in `banking_agent/prompt.py`:
- `INTENT_AGENT_PROMPT` - Intent classification logic and examples
- `CONCIERGE_INSTRUCTIONS` - Main agent behavior, response formatting, and guidelines

Key constraints to maintain:
- Voice responses ≤30 words for audio delivery
- Markdown formatting in text responses
- No fabricated information
- Follow-up questions only in `follow_up_questions` array

### Updating Response Schemas

Response models in `banking_agent/models.py` use Pydantic with Field descriptors:

```python
class YourSchema(BaseModel):
    field: str = Field(..., description="Detailed description for LLM understanding")
```

Changes to schema fields require updating agent `output_schema` parameter.

### RAG Configuration

Cognee configuration in `banking_agent/rag/ingest.py`:
- LLM provider: `cognee.config.set_llm_provider("openai")`
- Model: `cognee.config.set_llm_model("gpt-4o-mini")`
- API keys set via `cognee.config.set_llm_api_key()`

To use different embeddings or vector stores, modify the initialization in `initialize_cognee()`.

## Project Conventions

### Async/Await Pattern
All RAG operations are async. Tools that use RAG must be async functions and properly await results.

### Environment Variables
Use `python-dotenv` to load `.env` files. Never commit API keys. Each agent directory can have its own `.env`.

### Temperature Settings
Both intent and main agents use `temperature=0.1` for consistent, deterministic responses. Adjust in `generate_content_config` if needed.

### Import Structure
- Main agent: `from banking_agent.agent import root_agent`
- Models: `from banking_agent.models import AgentResponse, IntentGuardrailOutput`
- Prompts: `from banking_agent.prompt import CONCIERGE_INSTRUCTIONS`
- RAG: `from banking_agent.rag import search_knowledge, ingest_pdf`

### Session State Keys
When adding agents to the sequence, use meaningful `output_key` values that downstream agents can reference. Current keys:
- `user_intent` - Intent classification output from intent_agent

## Project Structure Best Practices

### What to Modify
- Agent implementations in `banking_agent/agent.py`
- Prompts in `banking_agent/prompt.py`
- Data models in `banking_agent/models.py`
- RAG custom logic in `banking_agent/rag/ingest.py` and `banking_agent/rag/retrieval.py`
- Test cases in `banking_agent/test_suite.evalset.json`
- Environment configurations in `.env` files

### What NOT to Modify
- **Never modify** `banking_agent/google/` - This is the ADK framework reference
- **Never modify** `banking_agent/rag/cognee/` - This is the Cognee library reference
- **Do not commit** `.env` files or API keys
- **Do not modify** `banking_agent/.adk/eval_history/` - Auto-generated evaluation results

### File Organization
The project follows this structure:
```
adk-learning/
├── banking_agent/              # Main agent implementation
│   ├── agent.py               # Agent definitions (intent + avery + root)
│   ├── prompt.py              # Agent instruction prompts
│   ├── models.py              # Pydantic response schemas
│   ├── test_suite.evalset.json # Test cases for evaluation
│   ├── .env                   # Environment variables (not in git)
│   ├── .adk/                  # ADK auto-generated files
│   ├── google/                # [REFERENCE ONLY] ADK framework
│   └── rag/                   # RAG module
│       ├── __init__.py        # Module exports
│       ├── ingest.py          # Document ingestion
│       ├── retrieval.py       # Search and retrieval
│       ├── example.py         # Usage examples
│       ├── .env               # RAG-specific env vars
│       └── cognee/            # [REFERENCE ONLY] Cognee library
├── tool_callback_agent/        # Simple example agent
└── .venv/                      # Python virtual environment
```

### Development Workflow

1. **Setup**: Activate venv and set up environment variables in `.env` files
2. **Develop**: Modify agent code, prompts, or models as needed
3. **Test Locally**: Use `adk run banking_agent` for interactive testing
4. **Evaluate**: Run `adk eval` against test cases before major changes
5. **Web Testing**: Use `adk web .` for UI-based testing and demos

### Debugging Tips

- Use `--print_detailed_results` with `adk eval` to see full conversation traces
- Check `banking_agent/.adk/eval_history/` for evaluation run details
- Enable verbose logging in ADK with logging level configurations
- For RAG issues, test ingestion/retrieval separately using `banking_agent/rag/example.py`
- Cognee stores data locally; use `reset_knowledge_base()` from `ingest.py` to clear state
