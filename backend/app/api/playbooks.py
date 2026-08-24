"""Playbook content endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import PlaybookChunk

router = APIRouter(prefix="/playbooks", tags=["playbooks"])


class PlaybookChunkResponse(BaseModel):
    id: str
    document_title: str
    section_title: str
    content: str
    chunk_index: int

    model_config = {"from_attributes": True}


class PlaybookListResponse(BaseModel):
    chunks: list[PlaybookChunkResponse]


@router.get("", response_model=PlaybookListResponse)
async def list_playbooks(db: AsyncSession = Depends(get_db)):
    """List all playbook chunks grouped by document."""
    result = await db.execute(
        select(PlaybookChunk).order_by(PlaybookChunk.document_title, PlaybookChunk.chunk_index)
    )
    chunks = result.scalars().all()
    return PlaybookListResponse(
        chunks=[
            PlaybookChunkResponse(
                id=str(c.id),
                document_title=c.document_title,
                section_title=c.section_title,
                content=c.content,
                chunk_index=c.chunk_index,
            )
            for c in chunks
        ]
    )


@router.get("/{chunk_id}", response_model=PlaybookChunkResponse)
async def get_playbook_chunk(chunk_id: str, db: AsyncSession = Depends(get_db)):
    """Get a specific playbook chunk by ID."""
    result = await db.execute(
        select(PlaybookChunk).where(PlaybookChunk.id == chunk_id)
    )
    chunk = result.scalar_one_or_none()
    if not chunk:
        raise HTTPException(status_code=404, detail="Playbook chunk not found")

    return PlaybookChunkResponse(
        id=str(chunk.id),
        document_title=chunk.document_title,
        section_title=chunk.section_title,
        content=chunk.content,
        chunk_index=chunk.chunk_index,
    )


@router.get("/search/{query}", response_model=PlaybookListResponse)
async def search_playbooks_by_title(query: str, db: AsyncSession = Depends(get_db)):
    """Search playbook chunks by document or section title."""
    result = await db.execute(
        select(PlaybookChunk).where(
            PlaybookChunk.document_title.ilike(f"%{query}%")
            | PlaybookChunk.section_title.ilike(f"%{query}%")
        ).order_by(PlaybookChunk.document_title, PlaybookChunk.chunk_index)
    )
    chunks = result.scalars().all()
    return PlaybookListResponse(
        chunks=[
            PlaybookChunkResponse(
                id=str(c.id),
                document_title=c.document_title,
                section_title=c.section_title,
                content=c.content,
                chunk_index=c.chunk_index,
            )
            for c in chunks
        ]
    )


class CreatePlaybookRequest(BaseModel):
    document_title: str
    section_title: str
    content: str


@router.post("", response_model=PlaybookChunkResponse, status_code=201)
async def create_playbook_chunk(
    body: CreatePlaybookRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create a new playbook chunk and embed it for RAG."""
    from app.services.embeddings import get_embedding

    # Get embedding for the new content
    embed_text = f"{body.document_title} / {body.section_title}: {body.content}"
    embedding = get_embedding(embed_text)

    # Find next chunk_index for this document
    from sqlalchemy import func
    max_idx = (await db.execute(
        select(func.max(PlaybookChunk.chunk_index))
        .where(PlaybookChunk.document_title == body.document_title)
    )).scalar_one_or_none() or -1

    chunk = PlaybookChunk(
        document_title=body.document_title,
        section_title=body.section_title,
        content=body.content,
        chunk_index=(max_idx or 0) + 1,
        embedding=embedding,
    )
    db.add(chunk)
    await db.commit()
    await db.refresh(chunk)

    return PlaybookChunkResponse(
        id=str(chunk.id),
        document_title=chunk.document_title,
        section_title=chunk.section_title,
        content=chunk.content,
        chunk_index=chunk.chunk_index,
    )
