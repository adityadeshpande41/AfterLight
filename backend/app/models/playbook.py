"""Playbook document chunks with vector embeddings for RAG."""

import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKey


class PlaybookChunk(Base, UUIDPrimaryKey, TimestampMixin):
    """A chunk of a playbook document with its embedding."""

    __tablename__ = "playbook_chunks"

    document_title: Mapped[str] = mapped_column(String(255), nullable=False)
    section_title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    # OpenAI text-embedding-3-small produces 1536-dimensional vectors
    embedding: Mapped[list] = mapped_column(Vector(1536), nullable=True)
