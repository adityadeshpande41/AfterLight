"""
RAG tools for agents — semantic search over playbook documents.

Agents call these to search for relevant playbook guidance.
Runs synchronously since OpenAI tool execution context is sync.
"""

import json

from sqlalchemy import create_engine, text

from app.config import settings
from app.services.embeddings import get_embedding

SYNC_URL = settings.database_url.replace("postgresql+asyncpg", "postgresql+psycopg2")


def search_playbooks(query: str, top_k: int = 3) -> str:
    """
    Search playbook documents for guidance on a specific topic.

    Args:
        query: Natural language query (e.g., "how to preserve camera footage after an incident")
        top_k: Number of results to return (default 3)

    Returns:
        JSON string with relevant playbook sections including source_id for citation verification
    """
    query_embedding = get_embedding(query)

    engine = create_engine(SYNC_URL)
    with engine.connect() as conn:
        result = conn.execute(
            text("""
                SELECT id, document_title, section_title, content,
                       embedding <=> :query_embedding AS distance
                FROM playbook_chunks
                ORDER BY embedding <=> :query_embedding
                LIMIT :top_k
            """),
            {"query_embedding": str(query_embedding), "top_k": top_k},
        )
        rows = result.fetchall()
    engine.dispose()

    RELEVANCE_THRESHOLD = 0.80
    results = []
    for row in rows:
        if row.distance <= RELEVANCE_THRESHOLD:
            results.append({
                "source_id": str(row.id),
                "document": row.document_title,
                "section": row.section_title,
                "content": row.content,
                "relevance_score": round(1 - row.distance, 3),
            })

    return json.dumps(results)


# Tool definition for OpenAI function calling
RAG_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_playbooks",
            "description": "Search approved playbook documents for guidance on a specific topic. Returns relevant sections with source_id for citation verification.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Natural language search query"},
                    "top_k": {"type": "integer", "description": "Number of results (default 3)"},
                },
                "required": ["query"],
            },
        },
    },
]

RAG_TOOL_FUNCTIONS = {
    "search_playbooks": search_playbooks,
}
