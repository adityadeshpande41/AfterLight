"""
Seed playbook documents into pgvector with embeddings.
Run: python seed_playbooks.py
"""

import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.models.playbook import PlaybookChunk
from app.services.embeddings import get_embeddings_batch

PLAYBOOKS = [
    {
        "document_title": "Entrance Safety Playbook",
        "sections": [
            {
                "section_title": "Recurring Entrance Incidents",
                "content": "When two or more entrance-related incidents occur within a 60-day window, the venue must escalate to a formal entrance safety review. This includes verifying floor surface condition, lighting levels, mat anchoring, and door-team staffing during peak egress hours. The review must be documented with timestamped photos and a signed action log."
            },
            {
                "section_title": "Entrance Inspection Protocol",
                "content": "Entrance inspections should be conducted every 30 minutes during peak hours (11 PM to 3 AM). Each inspection must verify: floor is dry and clear of debris, entrance mats are flush and anchored, lighting is functional, signage is visible, and queue barriers are stable. Log each inspection with time, inspector name, and pass/fail status."
            },
            {
                "section_title": "Slip and Fall Response",
                "content": "When a slip-and-fall occurs at the entrance: (1) Secure the area immediately and deploy wet-floor signage. (2) Photograph the condition that caused the fall within 5 minutes. (3) Record the exact time and weather conditions. (4) Identify and preserve camera footage covering the area. (5) Obtain contact information from any witnesses. (6) Complete the venue incident form within the same shift."
            },
        ],
    },
    {
        "document_title": "Evidence Preservation Playbook",
        "sections": [
            {
                "section_title": "Footage Retention",
                "content": "Camera footage related to an incident must be preserved within 24 hours of the event. Most venue CCTV systems overwrite footage on a 72-hour rolling basis. To preserve: (1) Identify all cameras with a view of the incident area. (2) Export the footage covering 30 minutes before and 30 minutes after the incident. (3) Save exports to a secure, write-protected location. (4) Log the camera ID, time range, and export confirmation in the evidence tracker. Failure to preserve footage within the retention window constitutes a critical evidence gap."
            },
            {
                "section_title": "Document Chain of Custody",
                "content": "Every piece of evidence must have a clear chain of custody. Record: who collected it, when, where it was stored, and who has accessed it since. Digital evidence should include file hashes. Physical evidence should be photographed in situ before being moved. Any break in chain of custody must be documented with an explanation."
            },
        ],
    },
    {
        "document_title": "Incident Documentation Playbook",
        "sections": [
            {
                "section_title": "Initial Report Requirements",
                "content": "Every incident report must capture within the first hour: (1) What happened — factual description without speculation. (2) When — exact time to the minute. (3) Where — specific location within the venue. (4) Who was involved — staff, guests, emergency services. (5) What response was taken — in chronological order. (6) What evidence exists — camera coverage, witnesses, physical evidence. The report must be written by a person who was present or who directly debriefed witnesses."
            },
            {
                "section_title": "Witness Statement Protocol",
                "content": "Witness statements should be collected within 24 hours while memory is fresh. Each statement must be: (1) Written or recorded in the witness's own words. (2) Include the witness's name, role, and contact information. (3) Signed and dated by the witness. (4) Stored securely with the incident file. Do not coach witnesses or suggest details. If a witness declines, document the refusal."
            },
        ],
    },
    {
        "document_title": "Venue Security Plan",
        "sections": [
            {
                "section_title": "Late-Night Coverage Standards",
                "content": "Between 11 PM and 3 AM, minimum security staffing is: 1 guard per 100 capacity at entry points, 1 roaming guard per 200 capacity inside the venue, and 1 supervisor coordinating radio communications. When incidents increase in frequency at a specific location, add a dedicated static post at that location for a minimum of 4 consecutive operating nights. Document the staffing adjustment and review after the trial period."
            },
            {
                "section_title": "Incident Escalation Matrix",
                "content": "Low severity: Security lead resolves, reports to manager by end of shift. Moderate severity: Manager is notified immediately, decides on EMS/police involvement, incident report due within 2 hours. High severity: EMS/police called immediately, venue manager on-scene within 15 minutes, area secured and preserved, evidence preservation triggered automatically, incident report due within 1 hour. All high-severity incidents trigger a 48-hour review meeting."
            },
        ],
    },
]


async def seed_playbooks():
    # Enable pgvector extension
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

    # Create table if not exists
    from app.models.base import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(engine, expire_on_commit=False)

    # Clear existing playbook data
    async with async_session() as session:
        await session.execute(text("DELETE FROM playbook_chunks"))
        await session.commit()

    # Prepare chunks
    chunks = []
    texts_to_embed = []
    for playbook in PLAYBOOKS:
        for i, section in enumerate(playbook["sections"]):
            chunks.append({
                "document_title": playbook["document_title"],
                "section_title": section["section_title"],
                "content": section["content"],
                "chunk_index": i,
            })
            # Embed with context: document title + section title + content
            embed_text = f"{playbook['document_title']} / {section['section_title']}: {section['content']}"
            texts_to_embed.append(embed_text)

    # Get embeddings from OpenAI (batch)
    print(f"Embedding {len(texts_to_embed)} playbook chunks...")
    embeddings = get_embeddings_batch(texts_to_embed)

    # Insert chunks with embeddings
    async with async_session() as session:
        for chunk_data, embedding in zip(chunks, embeddings):
            chunk = PlaybookChunk(
                document_title=chunk_data["document_title"],
                section_title=chunk_data["section_title"],
                content=chunk_data["content"],
                chunk_index=chunk_data["chunk_index"],
                embedding=embedding,
            )
            session.add(chunk)
        await session.commit()

    await engine.dispose()
    print(f"✓ Seeded {len(chunks)} playbook chunks with embeddings")


if __name__ == "__main__":
    asyncio.run(seed_playbooks())
