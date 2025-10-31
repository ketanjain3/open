# RAG Module for Banking Agent

This module provides a simple RAG (Retrieval-Augmented Generation) ingestion and retrieval mechanism using [cognee](https://github.com/topoteretes/cognee).

## Features

- **Document Ingestion**: Process PDFs and other documents into a knowledge base
- **Smart Retrieval**: Query the knowledge base using natural language
- **Context Generation**: Get formatted context to augment LLM prompts
- **Batch Processing**: Ingest multiple documents at once

## Installation

First, install cognee and its dependencies:

```bash
pip install cognee
```

You may also need to install additional dependencies depending on your setup:

```bash
# For PDF processing
pip install pypdf pymupdf

# If using OpenAI embeddings (default)
pip install openai
```

## Configuration

Cognee can be configured to use different LLM providers and vector stores. Set up environment variables as needed:

```bash
# For OpenAI (default)
export OPENAI_API_KEY="your-api-key"

# For Anthropic
export ANTHROPIC_API_KEY="your-api-key"

# For local models
# Configure in the code using cognee.config
```

## Usage

### Basic Ingestion

```python
import asyncio
from banking_agent.rag import ingest_pdf, initialize_cognee

async def ingest():
    # Initialize cognee
    await initialize_cognee()

    # Ingest a PDF
    result = await ingest_pdf("path/to/document.pdf")
    print(result)

asyncio.run(ingest())
```

### Batch Ingestion

```python
from banking_agent.rag import ingest_documents

async def batch_ingest():
    # Ingest all PDFs in a directory
    results = await ingest_documents(
        ["path/to/documents"],
        file_types=['.pdf', '.txt']
    )

    for result in results:
        print(f"{result['filename']}: {result['status']}")

asyncio.run(batch_ingest())
```

### Searching the Knowledge Base

```python
from banking_agent.rag import search_knowledge

async def search():
    results = await search_knowledge(
        "What is innovation?",
        limit=5
    )

    for result in results:
        print(result['content'])

asyncio.run(search())
```

### Getting Context for Prompts

```python
from banking_agent.rag import get_context_for_query

async def get_context():
    context = await get_context_for_query(
        "innovation metrics",
        max_tokens=2000
    )

    # Use this context in your agent prompt
    prompt = f"{context}\n\nUser question: How is innovation measured?"
    # ... pass to LLM

asyncio.run(get_context())
```

## Running the Example

An example script is provided to demonstrate the functionality:

```bash
cd banking_agent/rag
python example.py
```

## Integration with Banking Agent

To integrate RAG into your banking agent, you can create a retrieval tool:

```python
# In your agent.py
from .rag import search_knowledge, get_context_for_query
import asyncio

def search_documents(query: str):
    """
    Search the knowledge base for relevant information.

    Args:
        query: The search query
    """
    results = asyncio.run(search_knowledge(query, limit=3))
    return results

# Add to your agent's tools
avery_agent = LlmAgent(
    # ... other config
    tools=[get_investment_portfolio, search_documents],
)
```

## File Structure

```
rag/
├── __init__.py          # Module exports
├── ingest.py           # Document ingestion functions
├── retrieval.py        # Search and retrieval functions
├── example.py          # Example usage script
├── README.md           # This file
└── global-innovation-index.pdf  # Example document
```

## Advanced Usage

### Custom Configuration

```python
import cognee

# Configure LLM provider
cognee.config.set_llm_provider("anthropic")

# Configure vector store
# cognee.config.set_vector_db(...)
```

### Resetting the Knowledge Base

```python
from banking_agent.rag.ingest import reset_knowledge_base

async def reset():
    await reset_knowledge_base()
    print("Knowledge base cleared")

asyncio.run(reset())
```

## Notes

- Cognee processes documents and creates a knowledge graph with embeddings
- The first ingestion may take some time as it processes and embeds the content
- Search results are ranked by relevance using semantic similarity
- You can customize the chunking, embedding model, and retrieval strategies through cognee's configuration

## Troubleshooting

**Issue**: PDF processing errors
- **Solution**: Ensure you have `pypdf` or `pymupdf` installed

**Issue**: API key errors
- **Solution**: Set the appropriate environment variables for your LLM provider

**Issue**: Memory issues with large documents
- **Solution**: Process documents in smaller batches or increase available memory

## References

- [Cognee Documentation](https://github.com/topoteretes/cognee)
- [RAG Best Practices](https://www.anthropic.com/research/rag)
