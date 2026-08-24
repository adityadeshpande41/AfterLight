"""
Semantic cache for the Risk Copilot.

Uses pgvector to find semantically similar previous questions
and return cached answers without calling the LLM.

Cache scope:
- venue_id (each venue has isolated cache)
- Invalidated when venue context changes (incidents, evidence, actions, scores)

Eligibility:
- Only cache factual/reference answers
- Don't cache drafting, real-time, or action requests
"""

import json
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine, text

from app.config import settings
from app.services.embeddings import get_embedding

SYNC_URL = settings.database_url.replace("postgresql+asyncpg", "postgresql+psycopg2")

# Similarity threshold — lower distance = more similar
# 0.15 means the cached question must be very similar (cosine distance < 0.15)
SIMILARITY_THRESHOLD = 0.15

# Cache TTL
CACHE_TTL_HOURS = 24


class SemanticCache:
    def __init__(self, venue_id: str):
        self.venue_id = venue_id

    async def lookup(self, question: str) -> dict | None:
        """Check if a semantically similar question has been cached."""
        try:
            question_embedding = get_embedding(question)

            engine = create_engine(SYNC_URL)
            with engine.connect() as conn:
                # Check if cache table exists
                result = conn.execute(text(
                    """SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_name = 'copilot_cache'
                    )"""
                ))
                if not result.scalar():
                    engine.dispose()
                    return None

                # Find similar cached questions
                result = conn.execute(
                    text("""
                        SELECT response_json, question,
                               question_embedding <=> :embedding AS distance
                        FROM copilot_cache
                        WHERE venue_id = :venue_id
                          AND created_at > :cutoff
                        ORDER BY question_embedding <=> :embedding
                        LIMIT 1
                    """),
                    {
                        "embedding": str(question_embedding),
                        "venue_id": self.venue_id,
                        "cutoff": (datetime.now(timezone.utc) - timedelta(hours=CACHE_TTL_HOURS)).isoformat(),
                    },
                )
                row = result.fetchone()

            engine.dispose()

            if row and row.distance < SIMILARITY_THRESHOLD:
                return json.loads(row.response_json)
            return None

        except Exception:
            # Cache miss on any error — don't block the user
            return None

    async def store(self, question: str, response: dict):
        """Store a response in the semantic cache."""
        try:
            question_embedding = get_embedding(question)

            engine = create_engine(SYNC_URL)
            with engine.connect() as conn:
                # Ensure table exists
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS copilot_cache (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        venue_id VARCHAR(100) NOT NULL,
                        question TEXT NOT NULL,
                        question_embedding vector(1536),
                        response_json TEXT NOT NULL,
                        created_at TIMESTAMPTZ DEFAULT NOW()
                    )
                """))
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_copilot_cache_venue
                    ON copilot_cache (venue_id)
                """))

                # Insert
                conn.execute(
                    text("""
                        INSERT INTO copilot_cache (venue_id, question, question_embedding, response_json)
                        VALUES (:venue_id, :question, :embedding, :response_json)
                    """),
                    {
                        "venue_id": self.venue_id,
                        "question": question,
                        "embedding": str(question_embedding),
                        "response_json": json.dumps(response),
                    },
                )
                conn.commit()
            engine.dispose()

        except Exception:
            # Caching failure shouldn't break the response
            pass

    async def invalidate(self):
        """Clear cache for this venue (called when context changes)."""
        try:
            engine = create_engine(SYNC_URL)
            with engine.connect() as conn:
                conn.execute(
                    text("DELETE FROM copilot_cache WHERE venue_id = :venue_id"),
                    {"venue_id": self.venue_id},
                )
                conn.commit()
            engine.dispose()
        except Exception:
            pass
