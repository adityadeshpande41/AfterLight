"""
Embedding service using OpenAI text-embedding-3-small.

Used for:
- Embedding playbook chunks for RAG
- Embedding user queries for semantic search
"""

from openai import OpenAI

from app.config import settings

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536


def get_embedding(text: str) -> list[float]:
    """Get a single embedding vector for a text string."""
    client = OpenAI(api_key=settings.openai_api_key)
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text,
    )
    return response.data[0].embedding


def get_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """Get embeddings for multiple texts in one API call."""
    client = OpenAI(api_key=settings.openai_api_key)
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=texts,
    )
    return [item.embedding for item in response.data]
