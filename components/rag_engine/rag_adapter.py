import asyncio
from components.rag_engine.app.retriever import retrieve_documents


async def retrieve(query: str, top_k: int = 5) -> dict:
    """
    Domain-agnostic retrieval interface.
    Called by generic_handlers.py.
    Returns retrieved text chunks and their sources.
    """
    if not query.strip():
        return {
            "status": "success",
            "content": "No query provided.",
            "sources": [],
            "chunks": [],
        }

    # Run blocking ChromaDB vector search in a worker thread
    documents = await asyncio.to_thread(retrieve_documents, query, top_k)

    # Filter out empty/blank chunks (safe threshold of 30 chars)
    documents = [
        doc for doc in documents
        if len(doc.page_content.strip()) >= 30
    ]

    if not documents:
        return {
            "status": "success",
            "content": "No relevant information found in the knowledge base.",
            "sources": [],
            "chunks": [],
        }

    chunks = [doc.page_content for doc in documents]
    sources = [doc.metadata for doc in documents]

    # Combine chunks into a single context string for the Agent
    combined_context = "\n\n---\n\n".join(chunks)

    return {
        "status": "success",
        "content": combined_context,
        "sources": sources,
        "chunks": chunks,
    }
