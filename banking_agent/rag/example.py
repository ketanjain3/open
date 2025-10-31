"""
Example usage of the RAG ingestion and retrieval system.

This script demonstrates how to:
1. Initialize the cognee knowledge base
2. Ingest PDF documents
3. Search and retrieve information
"""

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
from ingest import initialize_cognee, ingest_pdf, ingest_documents, reset_knowledge_base
from retrieval import search_knowledge, get_context_for_query

# Load environment variables from .env file
load_dotenv()


async def main():
    """Main example function demonstrating RAG functionality."""

    print("=" * 60)
    print("RAG Ingestion & Retrieval Example")
    print("=" * 60)

    # Step 1: Initialize cognee
    print("\n1. Initializing cognee...")
    await initialize_cognee()

    # Step 2: Ingest the PDF document
    print("\n2. Ingesting PDF document...")
    rag_dir = Path(__file__).parent
    pdf_path = rag_dir / "global-innovation-index.pdf"

    if pdf_path.exists():
        result = await ingest_pdf(pdf_path)
        print(f"Ingestion result: {result}")
    else:
        print(f"PDF not found at: {pdf_path}")
        print("Please ensure global-innovation-index.pdf is in the rag/ directory")
        return

    # Step 3: Search the knowledge base
    print("\n3. Searching the knowledge base...")

    # Example queries
    queries = [
        "What is innovation?",
        "Which countries are mentioned?",
        "What are the key innovation metrics?",
    ]

    for query in queries:
        print(f"\n--- Query: '{query}' ---")
        results = await search_knowledge(query, limit=3)

        if results:
            for idx, result in enumerate(results, 1):
                print(f"\nResult {idx}:")
                content = result.get("content", str(result))
                # Truncate for display
                print(content[:300] + "..." if len(content) > 300 else content)
        else:
            print("No results found")

    # Step 4: Get formatted context for a prompt
    print("\n4. Getting formatted context for a prompt...")
    query = "innovation index metrics"
    context = await get_context_for_query(query, max_tokens=500)
    print(f"\nContext for '{query}':")
    print(context[:500] + "..." if len(context) > 500 else context)

    print("\n" + "=" * 60)
    print("Example completed!")
    print("=" * 60)


async def example_batch_ingestion():
    """Example of ingesting multiple documents at once."""

    print("\n--- Batch Ingestion Example ---")

    # Initialize
    await initialize_cognee()

    # Ingest all PDFs in the rag directory
    rag_dir = Path(__file__).parent
    result = await ingest_documents([rag_dir], file_types=['.pdf'])

    print(f"\nIngested {len(result)} documents")
    for r in result:
        print(f"  - {r['filename']}: {r['status']}")


async def example_reset():
    """Example of resetting the knowledge base."""

    print("\n--- Reset Knowledge Base Example ---")
    print("WARNING: This will delete all ingested data!")

    # Uncomment to actually reset:
    # await reset_knowledge_base()
    print("(Reset commented out for safety)")


if __name__ == "__main__":
    # Run the main example
    asyncio.run(main())

    # Uncomment to run other examples:
    # asyncio.run(example_batch_ingestion())
    # asyncio.run(example_reset())
