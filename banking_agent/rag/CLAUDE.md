# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with the RAG module.

## Module Overview

This is a RAG (Retrieval-Augmented Generation) module that provides document ingestion and intelligent retrieval capabilities for the banking agent. It uses Cognee, an open-source Python RAG framework, to process documents into a searchable knowledge base with embeddings and knowledge graphs.

## Core Architecture

### Two-Phase RAG Pipeline

1. **Ingestion Phase** (ingest.py)
   - Documents are processed through `cognee.add()` to add them to the queue
   - `cognee.cognify()` processes documents, creates embeddings, and builds knowledge graph
   - Configuration uses OpenAI's gpt-4o-mini for processing

2. **Retrieval Phase** (retrieval.py)
   - Three search types available via `SearchType` enum:
     - `SUMMARIES`: Returns processed, high-level summaries (default, best for most queries)
     - `CHUNKS`: Returns raw text chunks from documents
     - `NATURAL_LANGUAGE`: Natural language search mode
   - Results are ranked by semantic similarity

### Key Functions

**Ingestion (ingest.py)**:
- `initialize_cognee()`: Configures Cognee with OpenAI API key, sets provider to "openai" and model to "gpt-4o-mini", then prunes existing data
- `ingest_pdf(pdf_path)`: Single PDF ingestion - calls `cognee.add()` then `cognee.cognify()`
- `ingest_documents(paths, file_types)`: Batch ingestion supporting .pdf, .txt, .md, .docx
- `reset_knowledge_base()`: Clears all data using `cognee.prune` methods

**Retrieval (retrieval.py)**:
- `search_knowledge(query, limit, search_type)`: Main search function, returns list of dicts with content and metadata
- `get_context_for_query(query, max_tokens)`: Returns formatted string suitable for prompt augmentation (estimates 1 token ≈ 4 characters)
- `search_with_filters(query, filters, limit)`: Applies post-search filtering on results
- `get_all_documents_info()`: Placeholder for document metadata retrieval

## Integration with Banking Agent

The RAG module is integrated via the `search_documents` tool in agent.py:32-81:

```python
async def search_documents(query: str, limit: int = 5) -> str:
    # Configures cognee on each call
    # Calls search_knowledge(query, limit, "summaries")
    # Formats results as string for agent consumption
```

This tool is available to the Avery agent for answering investment-related questions.

## Development Workflow

### Initial Setup and Data Ingestion

```bash
# From rag/ directory
python example.py  # Runs full ingestion and test queries
```

### Testing Queries

```bash
python test_query.py  # Test search functionality
```

### Custom Ingestion

```python
from ingest import initialize_cognee, ingest_pdf
import asyncio

async def custom_ingest():
    await initialize_cognee()
    result = await ingest_pdf("path/to/document.pdf")
    print(result)

asyncio.run(custom_ingest())
```

## Environment Variables

Required in `.env`:
- `OPENAI_API_KEY`: Used for embeddings and document processing
- Automatically sets `LLM_API_KEY` in cognee's config

## Reference-Only Dependencies

### cognee/ - Cognee Library Source (READ-ONLY)

This directory contains the complete Cognee source code copied from `.venv` for reference purposes. Use this to understand:
- How `cognee.add()`, `cognee.cognify()`, and `cognee.search()` work internally
- Configuration options and customization points
- Vector database and knowledge graph implementation
- Search algorithms and ranking strategies

**IMPORTANT**: Do NOT modify any files in `cognee/`. This is strictly for understanding the framework internals when making technical decisions.

Key areas to reference:
- `cognee/api/v1/`: Core API functions (add, search, cognify)
- `cognee/modules/`: Processing modules for different document types
- `cognee/base_config.py`: Configuration system
- `cognee/infrastructure/`: Vector DB and storage backends

## Important Implementation Details

### Search Type Selection

- **Use "summaries"** (default) for most queries - provides processed, relevant information
- **Use "chunks"** when you need raw document text or specific quotes
- **Use "natural_language"** for complex semantic queries

### Result Formatting in agent.py

The `search_documents` tool in agent.py formats results as a string because:
1. Agent tools must return strings or primitive types
2. Results iterate through different possible keys: 'text', 'content', 'summary'
3. Empty results are filtered out before formatting

### Cognee Configuration Pattern

Cognee is configured on each search call (agent.py:50-56) rather than once at startup because:
- Ensures API key is always set correctly
- Allows per-request configuration if needed
- Follows the async pattern of the agent framework

### Knowledge Base Persistence

- Cognee stores data in a local database/vector store
- Data persists between runs unless `reset_knowledge_base()` is called
- `initialize_cognee()` calls `prune` methods to start fresh

### Error Handling

- All async functions use try-except blocks
- Search returns empty list `[]` on errors
- Ingestion returns status dicts with "success", "error", or "queued" status

## File Structure

```
rag/
├── ingest.py              # Document ingestion functions
├── retrieval.py           # Search and retrieval functions
├── example.py             # Complete usage example with ingestion and queries
├── test_query.py          # Query testing script
├── requirements.txt       # RAG-specific dependencies
├── README.md              # User-facing documentation
├── global-innovation-index.pdf  # Example document (26MB)
├── logs/                  # Cognee logs directory
├── cognee/                # [READ-ONLY] Cognee source for reference
└── __init__.py            # Module exports (empty)
```

## Testing Patterns

When testing RAG functionality:

1. **First ingest data**: Call `initialize_cognee()` then `ingest_pdf()` or `ingest_documents()`
2. **Then query**: Use `search_knowledge()` with appropriate search_type
3. **Verify results**: Check that results list is not empty and contains relevant content
4. **Test different search types**: Compare "summaries" vs "chunks" vs "natural_language" results

Example from test_query.py pattern:
```python
results = await search_knowledge("innovation metrics", limit=5, search_type="summaries")
for result in results:
    print(result.get('text') or result.get('content'))
```

## Common Issues and Solutions

### Issue: Empty search results
- **Check**: Has data been ingested? Run ingestion first.
- **Check**: Is OPENAI_API_KEY set correctly?
- **Try**: Different search_type parameter

### Issue: Ingestion fails
- **Check**: PDF file is valid and readable
- **Check**: Sufficient memory available (large PDFs require significant RAM)
- **Try**: Process documents in smaller batches

### Issue: Slow queries
- **Note**: First query after ingestion may be slow as indices are built
- **Solution**: Subsequent queries should be faster due to caching

## Dependencies

From requirements.txt:
- `cognee>=0.1.0`: Core RAG framework
- `python-dotenv>=1.0.0`: Environment variable management
- `pypdf>=3.0.0`, `pymupdf>=1.23.0`: PDF processing libraries
- `openai>=1.0.0`: OpenAI API client for embeddings

## Current Knowledge Base

The example data is `global-innovation-index.pdf` (26MB), which contains:
- Global innovation rankings and metrics
- Country-specific innovation data
- Technology and research insights
- Economic and development indicators

This aligns with the "investment_related_question" intent category in the main agent.
