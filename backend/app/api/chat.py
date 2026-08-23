"""
Risk Copilot chat endpoint.

A grounded, tool-equipped agent that answers venue questions
with guardrails, off-topic detection, and semantic caching.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.copilot import CopilotAgent

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    venue_id: str = "moonlight"  # Default for demo
    conversation_id: str | None = None


class Citation(BaseModel):
    source: str
    section: str | None = None
    content_preview: str | None = None


class SuggestedAction(BaseModel):
    title: str
    link: str | None = None


class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation]
    suggested_actions: list[SuggestedAction]
    is_cached: bool = False
    guardrail_triggered: bool = False
    guardrail_reason: str | None = None


@router.post("", response_model=ChatResponse)
async def chat(body: ChatRequest, db: AsyncSession = Depends(get_db)):
    """
    Send a message to the Risk Copilot.

    The agent will:
    1. Check guardrails (off-topic, unsafe, out-of-scope)
    2. Check semantic cache
    3. Use tools (SQL + RAG) to gather relevant data
    4. Compose a grounded answer with citations
    5. Cache the response if eligible
    """
    agent = CopilotAgent(venue_id=body.venue_id)
    result = await agent.answer(body.message)
    return ChatResponse(**result)
