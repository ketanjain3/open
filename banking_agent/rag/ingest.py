"""
RAG Ingestion Module using Cognee

This module provides functionality to ingest documents (particularly PDFs)
into a knowledge base using the cognee library.
"""

import os
from pathlib import Path
from typing import List, Union
import cognee


async def initialize_cognee():
    """Initialize cognee with default configuration."""
    # Configure cognee with API key from environment
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in environment variables")

    # Set the API key in cognee's config
    os.environ["LLM_API_KEY"] = api_key
    cognee.config.llm_api_key = api_key
    cognee.config.set_llm_api_key(api_key)
    print("API key configured")

    # Set LLM provider and model
    cognee.config.set_llm_provider("openai")
    cognee.config.set_llm_model("gpt-4o-mini")
    print("LLM provider and model configured")

    # Configure cognee - you can customize these settings
    await cognee.prune.prune_data()  # Clean previous data
    await cognee.prune.prune_system(metadata=True)

    print("Cognee initialized successfully")


async def ingest_pdf(pdf_path: Union[str, Path]) -> dict:
    """
    Ingest a single PDF file into the cognee knowledge base.

    Args:
        pdf_path: Path to the PDF file to ingest

    Returns:
        dict: Status information about the ingestion
    """
    pdf_path = Path(pdf_path)

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    if pdf_path.suffix.lower() != '.pdf':
        raise ValueError(f"File must be a PDF: {pdf_path}")

    print(f"Ingesting PDF: {pdf_path.name}")

    try:
        # Add the document to cognee
        await cognee.add(str(pdf_path))

        # Process the documents (this creates embeddings and knowledge graph)
        await cognee.cognify()

        print(f"Successfully ingested: {pdf_path.name}")

        return {
            "status": "success",
            "file": str(pdf_path),
            "filename": pdf_path.name
        }
    except Exception as e:
        print(f"Error ingesting {pdf_path.name}: {str(e)}")
        return {
            "status": "error",
            "file": str(pdf_path),
            "error": str(e)
        }


async def ingest_documents(
    document_paths: List[Union[str, Path]],
    file_types: List[str] = None
) -> List[dict]:
    """
    Ingest multiple documents into the cognee knowledge base.

    Args:
        document_paths: List of paths to documents (files or directories)
        file_types: List of file extensions to process (e.g., ['.pdf', '.txt'])
                   If None, processes all supported types

    Returns:
        List[dict]: Status information for each ingested document
    """
    if file_types is None:
        file_types = ['.pdf', '.txt', '.md', '.docx']

    results = []
    files_to_process = []

    # Collect all files to process
    for path in document_paths:
        path = Path(path)

        if path.is_file():
            if path.suffix.lower() in file_types:
                files_to_process.append(path)
        elif path.is_dir():
            for ext in file_types:
                files_to_process.extend(path.glob(f"**/*{ext}"))

    print(f"Found {len(files_to_process)} files to ingest")

    # Process each file
    for file_path in files_to_process:
        try:
            # Add the document to cognee
            await cognee.add(str(file_path))
            print(f"Added: {file_path.name}")

            results.append({
                "status": "queued",
                "file": str(file_path),
                "filename": file_path.name
            })
        except Exception as e:
            print(f"Error adding {file_path.name}: {str(e)}")
            results.append({
                "status": "error",
                "file": str(file_path),
                "error": str(e)
            })

    # Process all documents at once
    if files_to_process:
        try:
            print("Processing documents and building knowledge graph...")
            await cognee.cognify()
            print("All documents processed successfully")

            # Update status for all queued items
            for result in results:
                if result["status"] == "queued":
                    result["status"] = "success"
        except Exception as e:
            print(f"Error during cognify: {str(e)}")
            for result in results:
                if result["status"] == "queued":
                    result["status"] = "error"
                    result["error"] = f"Cognify failed: {str(e)}"

    return results


async def reset_knowledge_base():
    """
    Reset the entire knowledge base.
    Use with caution - this will delete all ingested data!
    """
    print("Resetting knowledge base...")
    await cognee.prune.prune_data()
    await cognee.prune.prune_system(metadata=True)
    print("Knowledge base reset complete")
