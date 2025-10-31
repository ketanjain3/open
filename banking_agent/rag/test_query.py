"""
Simple query test for the RAG system.
This script tests querying without re-ingesting (preserves existing data).
"""

import asyncio
import os
from dotenv import load_dotenv
import cognee
from retrieval import search_knowledge, get_context_for_query

# Load environment variables
load_dotenv()


async def test_queries():
    """Test querying the knowledge base with various questions."""

    # Configure cognee
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        os.environ["LLM_API_KEY"] = api_key
        cognee.config.llm_api_key = api_key
        cognee.config.set_llm_api_key(api_key)
        cognee.config.set_llm_provider("openai")
        cognee.config.set_llm_model("gpt-4o-mini")
        print("✓ Cognee configured\n")

    # Test queries about the Global Innovation Index
    queries = [
        "What is the Global Innovation Index?",
        "Which country ranks first in innovation?",
        "What are the key innovation metrics measured?",
        "Tell me about WIPO and its role",
        "What regions are covered in the report?",
    ]

    print("="  * 70)
    print("TESTING RAG KNOWLEDGE BASE QUERIES")
    print("=" * 70)

    for i, query in enumerate(queries, 1):
        print(f"\n{'='*70}")
        print(f"QUERY {i}: {query}")
        print(f"{'='*70}")

        try:
            # Search for relevant information
            results = await search_knowledge(query, limit=3, search_type="summaries")

            if results:
                print(f"\n✓ Found {len(results)} results:\n")
                for idx, result in enumerate(results, 1):
                    print(f"--- Result {idx} ---")
                    content = result.get("content", str(result))
                    # Display first 400 chars
                    display_content = content[:400] + "..." if len(content) > 400 else content
                    print(display_content)
                    print()
            else:
                print("✗ No results found")

        except Exception as e:
            print(f"✗ Error: {str(e)}")

        print()

    # Test context generation
    print("\n" + "="*70)
    print("TESTING CONTEXT GENERATION")
    print("="*70)

    context_query = "innovation rankings and metrics"
    print(f"\nGenerating context for: '{context_query}'")

    try:
        context = await get_context_for_query(context_query, max_tokens=1000)
        print(f"\n✓ Generated context ({len(context)} characters):\n")
        print(context[:800] + "..." if len(context) > 800 else context)
    except Exception as e:
        print(f"✗ Error: {str(e)}")

    print("\n" + "="*70)
    print("QUERY TEST COMPLETED")
    print("="*70)


if __name__ == "__main__":
    asyncio.run(test_queries())
