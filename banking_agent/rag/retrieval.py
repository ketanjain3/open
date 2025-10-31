"""
RAG Retrieval Module using Cognee

This module provides functionality to query the knowledge base
and retrieve relevant information.
"""

from typing import List, Dict, Any, Optional
import cognee


async def search_knowledge(
    query: str,
    limit: int = 5,
    search_type: str = "summaries"
) -> List[Dict[str, Any]]:
    """
    Search the knowledge base for information relevant to the query.

    Args:
        query: The search query string
        limit: Maximum number of results to return (default: 5)
        search_type: Type of search - "summaries" for processed summaries,
                    "chunks" for raw text chunks, or "natural_language" for NL search
                    (default: "summaries")

    Returns:
        List[Dict]: List of relevant results with their content and metadata
    """
    print(f"Searching knowledge base for: '{query}'")

    try:
        # Import SearchType enum from cognee
        from cognee.api.v1.search import SearchType

        # Map to SearchType enum
        search_type_map = {
            "summaries": SearchType.SUMMARIES,
            "chunks": SearchType.CHUNKS,
            "natural_language": SearchType.NATURAL_LANGUAGE,
        }

        search_type_enum = search_type_map.get(search_type, SearchType.SUMMARIES)

        #  Search using cognee - query first, then search type
        results = await cognee.search(
            query,
            search_type_enum
        )

        # Process and format results
        formatted_results = []

        if isinstance(results, list):
            for idx, result in enumerate(results[:limit]):
                if isinstance(result, dict):
                    formatted_results.append(result)
                else:
                    # If result is not a dict, convert it to one
                    formatted_results.append({
                        "content": str(result),
                        "rank": idx + 1
                    })
        else:
            # If results is a single item, wrap it in a list
            formatted_results = [{
                "content": str(results),
                "rank": 1
            }]

        print(f"Found {len(formatted_results)} results")
        return formatted_results

    except Exception as e:
        print(f"Error during search: {str(e)}")
        return []


async def get_context_for_query(
    query: str,
    max_tokens: int = 2000
) -> str:
    """
    Get formatted context from the knowledge base for a given query.
    This is useful for augmenting prompts with relevant information.

    Args:
        query: The query to search for
        max_tokens: Maximum approximate tokens to return (rough estimate)

    Returns:
        str: Formatted context string that can be added to prompts
    """
    results = await search_knowledge(query, limit=10)

    if not results:
        return "No relevant information found in the knowledge base."

    # Build context string
    context_parts = ["Relevant information from knowledge base:\n"]

    current_length = 0
    max_chars = max_tokens * 4  # Rough estimate: 1 token ≈ 4 characters

    for idx, result in enumerate(results, 1):
        content = result.get("content", str(result))

        # Check if adding this would exceed the limit
        if current_length + len(content) > max_chars:
            break

        context_parts.append(f"\n[Source {idx}]")
        context_parts.append(content)
        context_parts.append("\n")

        current_length += len(content)

    return "\n".join(context_parts)


async def search_with_filters(
    query: str,
    filters: Optional[Dict[str, Any]] = None,
    limit: int = 5
) -> List[Dict[str, Any]]:
    """
    Search with additional filters (if supported by cognee configuration).

    Args:
        query: The search query string
        filters: Optional dictionary of filters to apply
        limit: Maximum number of results to return

    Returns:
        List[Dict]: Filtered search results
    """
    # Note: Filter implementation depends on cognee's configuration
    # This is a placeholder for more advanced filtering

    results = await search_knowledge(query, limit=limit)

    if filters and results:
        # Basic filtering on the returned results
        filtered_results = []

        for result in results:
            matches = True

            for key, value in filters.items():
                if key in result and result[key] != value:
                    matches = False
                    break

            if matches:
                filtered_results.append(result)

        return filtered_results

    return results


async def get_all_documents_info() -> List[Dict[str, Any]]:
    """
    Get information about all documents in the knowledge base.

    Returns:
        List[Dict]: List of document metadata
    """
    try:
        # This will depend on cognee's API for listing documents
        # For now, this is a placeholder
        print("Retrieving document information from knowledge base...")

        # You might need to use cognee's internal API for this
        # This is a simplified version
        return [{
            "info": "Document listing depends on cognee's API",
            "note": "Implement based on your cognee version"
        }]

    except Exception as e:
        print(f"Error retrieving document info: {str(e)}")
        return []
